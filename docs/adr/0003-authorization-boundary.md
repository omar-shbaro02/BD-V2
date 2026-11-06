# ADR 0003: Authentication and Human Authorization boundary

- Status: Accepted for local/conformity implementation only
- Date: 2026-10-09

## Decision

Use a signed test-principal adapter for local/conformity API tests. The server,
not a request body, establishes actor identity and `HUMAN` actor kind. Only this
boundary may create final human decision events.

A production identity provider is not selected and production deployment is not
authorized. Before any future deployment, replace the adapter and rerun all
authority tests.

