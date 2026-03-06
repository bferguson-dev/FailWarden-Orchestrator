"""Runbook compile and validation layer for FailWarden V1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jinja2 import (
    Environment,
    StrictUndefined,
    TemplateSyntaxError,
    UndefinedError,
    select_autoescape,
)
from jsonschema import Draft202012Validator

from failwarden_orchestrator.models import (
    CompiledRunbook,
    CompiledStep,
    EndStep,
    EscalateNotify,
    EscalateStep,
    SSHExpect,
    SSHStep,
)
from failwarden_orchestrator.validation import RunbookValidationError, ValidationIssue


class RunbookCompiler:
    """Compiles YAML runbooks into validated, execution-ready models."""

    def __init__(self, schema_path: Path | None = None) -> None:
        default_path = Path(__file__).parent / "schema" / "runbook-v1.schema.json"
        self.schema_path = schema_path or default_path
        self.schema = self._load_schema(self.schema_path)
        self.validator = Draft202012Validator(self.schema)
        self.jinja = Environment(
            undefined=StrictUndefined,
            autoescape=select_autoescape(
                disabled_extensions=("yml", "yaml", "txt"),
                default_for_string=False,
                default=False,
            ),
        )

    def compile_file(
        self,
        runbook_path: str | Path,
        runtime_vars: dict[str, Any] | None = None,
    ) -> CompiledRunbook:
        """Compile runbook YAML and return validated in-memory model."""
        path = Path(runbook_path)
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)

        if not isinstance(loaded, dict):
            issue = ValidationIssue(
                code="RBK101",
                message="Runbook root must be a YAML object",
                path="$",
                value=repr(loaded),
            )
            raise RunbookValidationError([issue])

        compiled = self.compile_dict(loaded, runtime_vars=runtime_vars)
        return compiled

    def compile_dict(
        self,
        runbook_data: dict[str, Any],
        runtime_vars: dict[str, Any] | None = None,
    ) -> CompiledRunbook:
        """Compile already-loaded runbook data into typed model."""
        runtime = runtime_vars or {}
        issues: list[ValidationIssue] = []

        issues.extend(self._schema_issues(runbook_data))
        issues.extend(self._semantic_issues(runbook_data))
        issues.extend(self._template_allowlist_issues(runbook_data))

        if issues:
            raise RunbookValidationError(sorted(issues, key=lambda item: item.path))

        rendered, template_issues = self._render_templates(runbook_data, runtime)
        if template_issues:
            raise RunbookValidationError(template_issues)

        model = self._build_model(rendered)
        return model

    @staticmethod
    def _load_schema(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _schema_issues(self, data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for error in sorted(self.validator.iter_errors(data), key=lambda err: err.path):
            code = self._map_schema_error_code(
                error.validator, error.message, error.instance
            )
            path = self._json_path(error.path)
            issues.append(
                ValidationIssue(
                    code=code,
                    message=error.message,
                    path=path,
                    value=repr(error.instance),
                )
            )
        return issues

    @staticmethod
    def _map_schema_error_code(
        validator: str,
        message: str,
        instance: object,
    ) -> str:
        if validator == "required":
            return "RBK101"
        if validator == "additionalProperties":
            return "RBK102"
        if validator == "minItems":
            return "RBK103"
        if validator == "oneOf":
            if (
                isinstance(message, str)
                and "is not valid under any of the given schemas" in message
            ):
                if isinstance(instance, dict):
                    step_type = instance.get("type")
                    if step_type in {"ssh", "escalate", "end"}:
                        return "RBK102"
            return "RBK105"
        return "RBK101"

    def _semantic_issues(self, data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        steps = data.get("steps", [])
        if not isinstance(steps, list):
            return issues

        seen: set[str] = set()
        duplicates: set[str] = set()
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            step_id = step.get("id")
            if isinstance(step_id, str):
                if step_id in seen:
                    duplicates.add(step_id)
                    issues.append(
                        ValidationIssue(
                            code="RBK104",
                            message=f"Duplicate step id '{step_id}'",
                            path=f"$.steps[{idx}].id",
                            value=repr(step_id),
                        )
                    )
                seen.add(step_id)

        if duplicates:
            return issues

        step_map: dict[str, dict[str, Any]] = {
            step["id"]: step
            for step in steps
            if isinstance(step, dict) and isinstance(step.get("id"), str)
        }

        entry = data.get("entry_step")
        if isinstance(entry, str) and entry not in step_map:
            issues.append(
                ValidationIssue(
                    code="RBK201",
                    message=f"entry_step '{entry}' does not exist",
                    path="$.entry_step",
                    value=repr(entry),
                )
            )

        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            step_type = step.get("type")
            if step_type != "ssh":
                continue
            for branch_key in ("on_success", "on_failure"):
                branch_target = step.get(branch_key)
                if isinstance(branch_target, str) and branch_target not in step_map:
                    issues.append(
                        ValidationIssue(
                            code="RBK202",
                            message=(
                                f"Branch target '{branch_target}' does not exist "
                                f"for '{branch_key}'"
                            ),
                            path=f"$.steps[{idx}].{branch_key}",
                            value=repr(branch_target),
                        )
                    )

        if issues:
            return issues

        graph = self._build_graph(step_map)

        if self._has_cycle(graph):
            issues.append(
                ValidationIssue(
                    code="RBK204",
                    message="Cycle detected in runbook graph",
                    path="$.steps",
                    value="'cycle'",
                )
            )
            return issues

        if isinstance(entry, str):
            reachable = self._reachable_steps(graph, entry)
            for step_id in step_map:
                if step_id not in reachable:
                    issues.append(
                        ValidationIssue(
                            code="RBK203",
                            message=f"Unreachable step '{step_id}'",
                            path="$.steps",
                            value=repr(step_id),
                        )
                    )

        return issues

    @staticmethod
    def _build_graph(step_map: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = {step_id: set() for step_id in step_map}
        for step_id, step in step_map.items():
            if step.get("type") != "ssh":
                continue
            success = step.get("on_success")
            failure = step.get("on_failure")
            if isinstance(success, str):
                graph[step_id].add(success)
            if isinstance(failure, str):
                graph[step_id].add(failure)
        return graph

    @staticmethod
    def _has_cycle(graph: dict[str, set[str]]) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for neighbor in graph.get(node, set()):
                if dfs(neighbor):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(dfs(node) for node in graph)

    @staticmethod
    def _reachable_steps(graph: dict[str, set[str]], entry: str) -> set[str]:
        seen: set[str] = set()
        stack = [entry]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            for neighbor in graph.get(current, set()):
                if neighbor not in seen:
                    stack.append(neighbor)
        return seen

    def _template_allowlist_issues(self, data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        steps = data.get("steps", [])
        if not isinstance(steps, list):
            return issues

        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue

            prohibited_keys = [
                "id",
                "type",
                "name",
                "on_success",
                "on_failure",
                "timeout",
                "retries",
                "retry_delay",
            ]
            for key in prohibited_keys:
                value = step.get(key)
                if self._contains_template(value):
                    issues.append(
                        ValidationIssue(
                            code="RBK403",
                            message=f"Template not allowed in field '{key}'",
                            path=f"$.steps[{idx}].{key}",
                            value=repr(value),
                        )
                    )

        return issues

    def _render_templates(
        self,
        data: dict[str, Any],
        runtime_vars: dict[str, Any],
    ) -> tuple[dict[str, Any], list[ValidationIssue]]:
        issues: list[ValidationIssue] = []
        rendered = dict(data)

        raw_vars = data.get("vars", {})
        rendered_vars: dict[str, Any] = {}
        if isinstance(raw_vars, dict):
            for key, value in raw_vars.items():
                if isinstance(value, str):
                    context = {**runtime_vars, **rendered_vars, **raw_vars}
                    rendered_value, issue = self._render_string(
                        value,
                        context,
                        path=f"$.vars.{key}",
                    )
                    if issue:
                        issues.append(issue)
                    else:
                        rendered_vars[key] = rendered_value
                else:
                    rendered_vars[key] = value

        render_context = {**runtime_vars, **rendered_vars}
        rendered["vars"] = rendered_vars

        steps = data.get("steps", [])
        rendered_steps: list[dict[str, Any]] = []
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                rendered_steps.append(step)
                continue
            step_copy = dict(step)

            command = step_copy.get("command")
            if isinstance(command, str):
                value, issue = self._render_string(
                    command,
                    render_context,
                    path=f"$.steps[{idx}].command",
                )
                if issue:
                    issues.append(issue)
                else:
                    step_copy["command"] = value

            summary = step_copy.get("summary")
            if isinstance(summary, str):
                value, issue = self._render_string(
                    summary,
                    render_context,
                    path=f"$.steps[{idx}].summary",
                )
                if issue:
                    issues.append(issue)
                else:
                    step_copy["summary"] = value

            notify = step_copy.get("notify")
            if isinstance(notify, dict):
                notify_copy = dict(notify)
                for field_name in ("title", "message"):
                    field_value = notify_copy.get(field_name)
                    if not isinstance(field_value, str):
                        continue
                    value, issue = self._render_string(
                        field_value,
                        render_context,
                        path=f"$.steps[{idx}].notify.{field_name}",
                    )
                    if issue:
                        issues.append(issue)
                    else:
                        notify_copy[field_name] = value
                step_copy["notify"] = notify_copy

            rendered_steps.append(step_copy)

        rendered["steps"] = rendered_steps
        return rendered, issues

    def _render_string(
        self,
        template_text: str,
        context: dict[str, Any],
        path: str,
    ) -> tuple[str, ValidationIssue | None]:
        try:
            template = self.jinja.from_string(template_text)
            return template.render(context), None
        except UndefinedError as exc:
            issue = ValidationIssue(
                code="RBK401",
                message=f"Undefined template variable: {exc}",
                path=path,
                value=repr(template_text),
            )
            return "", issue
        except TemplateSyntaxError as exc:
            issue = ValidationIssue(
                code="RBK402",
                message=f"Template syntax error: {exc}",
                path=path,
                value=repr(template_text),
            )
            return "", issue

    @staticmethod
    def _contains_template(value: object) -> bool:
        if not isinstance(value, str):
            return False
        return "{{" in value or "{%" in value

    @staticmethod
    def _json_path(parts: Any) -> str:
        path = "$"
        for part in parts:
            if isinstance(part, int):
                path += f"[{part}]"
            else:
                path += f".{part}"
        return path

    @staticmethod
    def _build_model(data: dict[str, Any]) -> CompiledRunbook:
        steps = data.get("steps", [])
        compiled_steps: list[CompiledStep] = []
        steps_by_id: dict[str, CompiledStep] = {}

        for step in steps:
            step_type = step["type"]
            if step_type == "ssh":
                expect = step["expect"]
                compiled = SSHStep(
                    id=step["id"],
                    type="ssh",
                    name=step["name"],
                    command=step["command"],
                    expect=SSHExpect(
                        exit_code=expect["exit_code"],
                        stdout_contains=expect.get("stdout_contains"),
                        stderr_contains=expect.get("stderr_contains"),
                    ),
                    timeout=step["timeout"],
                    retries=step["retries"],
                    retry_delay=step["retry_delay"],
                    on_success=step["on_success"],
                    on_failure=step["on_failure"],
                )
            elif step_type == "escalate":
                notify = step["notify"]
                compiled = EscalateStep(
                    id=step["id"],
                    type="escalate",
                    name=step["name"],
                    notify=EscalateNotify(
                        slack_enabled=notify["slack_enabled"],
                        email_enabled=notify["email_enabled"],
                        slack_channel=notify.get("slack_channel"),
                        email_to=notify.get("email_to"),
                        title=notify.get("title"),
                        message=notify.get("message"),
                    ),
                )
            else:
                compiled = EndStep(
                    id=step["id"],
                    type="end",
                    name=step["name"],
                    summary=step.get("summary"),
                )
            compiled_steps.append(compiled)
            steps_by_id[compiled.id] = compiled

        return CompiledRunbook(
            name=data["name"],
            description=data["description"],
            version=data.get("version"),
            vars=data["vars"],
            entry_step=data["entry_step"],
            steps_in_order=compiled_steps,
            steps_by_id=steps_by_id,
        )
