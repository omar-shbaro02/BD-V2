# ADR 0004: Agent runtime and model configuration

- Status: Accepted
- Date: 2026-10-09

## Decision

Use the OpenAI Agents SDK for Python for exactly five specialists. Keep the model
identifier and tracing controls in environment-backed configuration. Do not place
a model name in the domain schema and do not create agents during application
startup before Phase 5.

The deterministic application Orchestrator remains the owner of persistence,
sequencing, dependency checks, and approval boundaries.

