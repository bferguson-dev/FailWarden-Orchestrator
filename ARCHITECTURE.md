# ARCHITECTURE

## Intent

FailWarden Orchestrator is intentionally small and modular.

## Core Layers

- CLI layer
- Schema and compile layer
- Execution engine
- Executor layer (SSH only in V1)
- Notifier layer (Slack and email)
- Persistence layer (SQLite)
- Audit layer

## Design Constraints

- Validation before execution
- Explicit branching in runbook YAML
- Conservative defaults and security-first behavior
- Clear contracts between components
