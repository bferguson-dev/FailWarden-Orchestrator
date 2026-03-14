"""FailWarden Orchestrator CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from textwrap import dedent

import yaml

from failwarden_orchestrator import __version__
from failwarden_orchestrator.audit import AuditLogger
from failwarden_orchestrator.compiler import RunbookCompiler
from failwarden_orchestrator.engine import ExecutionEngine
from failwarden_orchestrator.executors.base import ExecutionResult
from failwarden_orchestrator.executors.ssh import SSHAuthConfig, SSHExecutor, SSHTarget
from failwarden_orchestrator.notifiers import EmailNotifier, SlackNotifier
from failwarden_orchestrator.persistence import SQLiteAuditStore
from failwarden_orchestrator.reporting import build_run_summary, write_run_summary_json
from failwarden_orchestrator.validation import RunbookValidationError


class _NoopExecutor:
    """Executor used when dry-run mode is enabled."""

    def execute(self, command: str, timeout_seconds: int) -> ExecutionResult:
        del command
        del timeout_seconds
        return ExecutionResult(
            success=False,
            output="",
            error="dry-run does not execute remote commands",
            exit_status=None,
            duration_ms=0,
            metadata={"executor": "noop"},
        )


def _parser_formatter() -> type[argparse.HelpFormatter]:
    return argparse.ArgumentDefaultsHelpFormatter


def _env_default(name: str, fallback: str) -> str:
    """Return one string default from the environment or a fallback."""
    return os.getenv(name, fallback)


def _env_default_int(name: str, fallback: int) -> int:
    """Return one integer default from the environment or a fallback."""
    value = os.getenv(name)
    if value is None:
        return fallback
    return int(value)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="fwo",
        description="FailWarden Orchestrator",
        formatter_class=_parser_formatter(),
        epilog=dedent(
            """
            Examples:
              fwo compile --runbook runbooks/linux_service_down.yaml
              fwo compile --runbook runbooks/linux_service_down.yaml --json
              fwo run --runbook runbooks/linux_service_down.yaml \\
                --target linux-web-01 --host 10.0.0.10 --user ubuntu \\
                --ssh-key ~/.ssh/id_ed25519
              fwo run --runbook runbooks/linux_service_down.yaml \\
                --target linux-web-01 --host 10.0.0.10 --user ubuntu \\
                --ssh-key ~/.ssh/id_ed25519 --dry-run --json
            """
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_cmd = subparsers.add_parser(
        "compile",
        help="Validate and compile a runbook",
        formatter_class=_parser_formatter(),
        description="Validate a YAML runbook and print a compile summary.",
    )
    compile_cmd.add_argument("--runbook", required=True, help="Path to YAML runbook")
    compile_cmd.add_argument(
        "--var",
        action="append",
        default=[],
        help="Template variable in key=value format (repeatable)",
    )
    compile_cmd.add_argument(
        "--json",
        action="store_true",
        help="Emit compile result as JSON",
    )

    run_cmd = subparsers.add_parser(
        "run",
        help="Run a compiled runbook",
        formatter_class=_parser_formatter(),
        description="Execute a compiled runbook against one SSH target.",
    )
    run_cmd.add_argument("--runbook", required=True, help="Path to YAML runbook")
    run_cmd.add_argument(
        "--target", required=True, help="Target host alias for audit context"
    )
    run_cmd.add_argument("--host", required=True, help="Target host for SSH")
    run_cmd.add_argument("--user", required=True, help="SSH username")
    run_cmd.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    run_cmd.add_argument(
        "--ssh-key",
        default=os.getenv("FWO_SSH_KEY_PATH"),
        help="SSH private key path",
    )
    run_cmd.add_argument(
        "--ssh-password-env",
        default=None,
        help="Environment variable name holding SSH password",
    )
    run_cmd.add_argument(
        "--var",
        action="append",
        default=[],
        help="Template variable in key=value format (repeatable)",
    )
    run_cmd.add_argument(
        "--db-path",
        default=_env_default("FWO_DB_PATH", ".data/fwo.sqlite3"),
        help="SQLite path",
    )
    run_cmd.add_argument(
        "--audit-dir",
        default=_env_default("FWO_AUDIT_DIR", ".audit"),
        help="Audit log directory",
    )
    run_cmd.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate run path without executing remote commands",
    )
    run_cmd.add_argument(
        "--json",
        action="store_true",
        help="Emit run result as JSON",
    )
    run_cmd.add_argument(
        "--summary-json",
        default=None,
        help="Write a detailed run summary JSON artifact to this path",
    )

    show_run_cmd = subparsers.add_parser(
        "show-run",
        help="Show a persisted execution summary",
        formatter_class=_parser_formatter(),
        description="Render one execution summary from SQLite audit history.",
    )
    show_run_cmd.add_argument(
        "--execution-id",
        required=True,
        help="Execution identifier to load from the audit store",
    )
    show_run_cmd.add_argument(
        "--db-path",
        default=".data/fwo.sqlite3",
        help="SQLite path",
    )
    show_run_cmd.add_argument(
        "--audit-dir",
        default=".audit",
        help="Audit log directory",
    )
    show_run_cmd.add_argument(
        "--json",
        action="store_true",
        help="Emit execution summary as JSON",
    )

    return parser


def parse_vars(pairs: list[str]) -> dict[str, str]:
    """Parse repeated key=value strings into a dict."""
    parsed: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            msg = f"Invalid --var format '{pair}', expected key=value"
            raise ValueError(msg)
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            msg = f"Invalid --var key in '{pair}'"
            raise ValueError(msg)
        parsed[key] = value
    return parsed


def build_notifiers_from_env() -> list[object]:
    """Create concrete notifiers from environment configuration."""
    notifiers: list[object] = []

    slack_webhook = os.getenv("FWO_SLACK_WEBHOOK_URL")
    slack_channel = os.getenv("FWO_SLACK_CHANNEL")
    if slack_webhook:
        notifiers.append(
            SlackNotifier(
                webhook_url=slack_webhook,
                default_channel=slack_channel,
            )
        )

    smtp_host = os.getenv("FWO_SMTP_HOST")
    if smtp_host:
        smtp_port = int(os.getenv("FWO_SMTP_PORT", "587"))
        smtp_user = os.getenv("FWO_SMTP_USERNAME")
        smtp_password = os.getenv("FWO_SMTP_PASSWORD")
        from_address = os.getenv("FWO_SMTP_FROM", "failwarden@example.local")
        use_tls = os.getenv("FWO_SMTP_USE_TLS", "true").lower() == "true"
        notifiers.append(
            EmailNotifier(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_username=smtp_user,
                smtp_password=smtp_password,
                from_address=from_address,
                use_tls=use_tls,
            )
        )

    return notifiers


def _emit_json(payload: dict[str, object]) -> None:
    """Write one JSON payload to stdout."""
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_run_summary(summary: dict[str, object]) -> None:
    """Write one readable execution summary."""
    execution = summary["execution"]
    stats = summary["stats"]
    print("Execution summary")
    print(f"  execution_id: {execution['id']}")
    print(f"  runbook: {execution['runbook_name']}")
    print(f"  target: {execution['target']}")
    print(f"  status: {execution['status']}")
    print(f"  dry_run: {execution['dry_run']}")
    print(f"  started_at: {execution['started_at']}")
    print(f"  ended_at: {execution['ended_at']}")
    print(f"  step_attempts: {stats['step_attempt_count']}")
    print(f"  notifications: {stats['notification_count']}")
    if summary["audit_log_path"] is not None:
        print(f"  audit_log: {summary['audit_log_path']}")
    if summary["audit_jsonl_path"] is not None:
        print(f"  audit_jsonl: {summary['audit_jsonl_path']}")


def cmd_compile(runbook_path: str, vars_pairs: list[str], *, json_output: bool) -> int:
    """Compile command implementation."""
    compiler = RunbookCompiler()
    runtime_vars = parse_vars(vars_pairs)
    compiled = compiler.compile_file(runbook_path, runtime_vars=runtime_vars)

    if json_output:
        _emit_json(
            {
                "entry_step": compiled.entry_step,
                "name": compiled.name,
                "runbook_path": str(runbook_path),
                "step_count": len(compiled.steps_in_order),
                "step_ids": [step.id for step in compiled.steps_in_order],
                "version": compiled.version,
            }
        )
        return 0

    print("Compile OK")
    print(f"  name: {compiled.name}")
    print(f"  entry_step: {compiled.entry_step}")
    print(f"  step_count: {len(compiled.steps_in_order)}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run command implementation."""
    compiler = RunbookCompiler()
    runtime_vars = parse_vars(args.var)
    compiled = compiler.compile_file(args.runbook, runtime_vars=runtime_vars)

    store = SQLiteAuditStore(Path(args.db_path))
    store.initialize()
    logger = AuditLogger(Path(args.audit_dir))

    if args.dry_run:
        executor = _NoopExecutor()
    else:
        ssh_password = None
        if args.ssh_password_env:
            ssh_password = os.getenv(args.ssh_password_env)
            if ssh_password is None:
                msg = f"SSH password env var '{args.ssh_password_env}' is not set."
                raise ValueError(msg)
        executor = SSHExecutor(
            target=SSHTarget(host=args.host, user=args.user, port=args.port),
            auth=SSHAuthConfig(key_path=args.ssh_key, password=ssh_password),
            connect_timeout_seconds=_env_default_int("FWO_SSH_CONNECT_TIMEOUT", 10),
            strict_host_key=True,
        )

    engine = ExecutionEngine(
        executor,
        audit_store=store,
        audit_logger=logger,
        notifiers=build_notifiers_from_env(),
    )

    result = engine.run(
        compiled,
        target=args.target,
        dry_run=args.dry_run,
    )

    if args.summary_json:
        summary = build_run_summary(
            store,
            result.execution_id,
            audit_dir=args.audit_dir,
        )
        write_run_summary_json(args.summary_json, summary)

    if args.json:
        _emit_json(
            {
                "attempts": result.attempts,
                "dry_run": args.dry_run,
                "dry_run_branch_map": result.dry_run_branch_map,
                "execution_id": result.execution_id,
                "final_status": result.final_status,
                "runbook": compiled.name,
                "step_path": result.step_path,
                "target": args.target,
            }
        )
        return 0

    print("Run complete")
    print(f"  execution_id: {result.execution_id}")
    print(f"  final_status: {result.final_status}")
    print(f"  attempts: {result.attempts}")
    print(f"  step_path: {','.join(result.step_path)}")
    if args.summary_json:
        print(f"  summary_json: {args.summary_json}")
    if result.dry_run_branch_map is not None:
        print("  dry_run_branch_map:")
        print(json.dumps(result.dry_run_branch_map, indent=2, sort_keys=True))

    return 0


def cmd_show_run(args: argparse.Namespace) -> int:
    """Show one persisted execution summary."""
    store = SQLiteAuditStore(Path(args.db_path))
    store.initialize()
    summary = build_run_summary(
        store,
        args.execution_id,
        audit_dir=args.audit_dir,
    ).to_dict()
    if args.json:
        _emit_json(summary)
    else:
        _print_run_summary(summary)
    return 0


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "compile":
            return cmd_compile(args.runbook, args.var, json_output=args.json)
        if args.command == "run":
            return cmd_run(args)
        if args.command == "show-run":
            return cmd_show_run(args)
    except RunbookValidationError as exc:
        print("Runbook validation failed:", file=sys.stderr)
        for issue in exc.issues:
            print(f"  {issue.format_human()}", file=sys.stderr)
        return 2
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    msg = f"Unknown command '{args.command}'"
    raise ValueError(msg)


if __name__ == "__main__":
    raise SystemExit(main())
