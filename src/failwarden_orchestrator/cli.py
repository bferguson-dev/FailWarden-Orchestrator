"""FailWarden Orchestrator CLI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from failwarden_orchestrator.audit import AuditLogger
from failwarden_orchestrator.compiler import RunbookCompiler
from failwarden_orchestrator.engine import ExecutionEngine
from failwarden_orchestrator.executors.base import ExecutionResult
from failwarden_orchestrator.executors.ssh import SSHAuthConfig, SSHExecutor, SSHTarget
from failwarden_orchestrator.notifiers import EmailNotifier, SlackNotifier
from failwarden_orchestrator.persistence import SQLiteAuditStore


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


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(prog="fwo", description="FailWarden Orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_cmd = subparsers.add_parser(
        "compile", help="Validate and compile a runbook"
    )
    compile_cmd.add_argument("--runbook", required=True, help="Path to YAML runbook")
    compile_cmd.add_argument(
        "--var",
        action="append",
        default=[],
        help="Template variable in key=value format (repeatable)",
    )

    run_cmd = subparsers.add_parser("run", help="Run a compiled runbook")
    run_cmd.add_argument("--runbook", required=True, help="Path to YAML runbook")
    run_cmd.add_argument(
        "--target", required=True, help="Target host alias for audit context"
    )
    run_cmd.add_argument("--host", required=True, help="Target host for SSH")
    run_cmd.add_argument("--user", required=True, help="SSH username")
    run_cmd.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    run_cmd.add_argument("--ssh-key", default=None, help="SSH private key path")
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
        default=".data/fwo.sqlite3",
        help="SQLite path (default: .data/fwo.sqlite3)",
    )
    run_cmd.add_argument(
        "--audit-dir",
        default=".audit",
        help="Audit log directory (default: .audit)",
    )
    run_cmd.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate run path without executing remote commands",
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


def cmd_compile(runbook_path: str, vars_pairs: list[str]) -> int:
    """Compile command implementation."""
    compiler = RunbookCompiler()
    runtime_vars = parse_vars(vars_pairs)
    compiled = compiler.compile_file(runbook_path, runtime_vars=runtime_vars)

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
        executor = SSHExecutor(
            target=SSHTarget(host=args.host, user=args.user, port=args.port),
            auth=SSHAuthConfig(key_path=args.ssh_key, password=ssh_password),
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

    print("Run complete")
    print(f"  execution_id: {result.execution_id}")
    print(f"  final_status: {result.final_status}")
    print(f"  step_path: {','.join(result.step_path)}")
    if result.dry_run_branch_map is not None:
        print("  dry_run_branch_map:")
        print(json.dumps(result.dry_run_branch_map, indent=2, sort_keys=True))

    return 0


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "compile":
        return cmd_compile(args.runbook, args.var)
    if args.command == "run":
        return cmd_run(args)

    msg = f"Unknown command '{args.command}'"
    raise ValueError(msg)


if __name__ == "__main__":
    raise SystemExit(main())
