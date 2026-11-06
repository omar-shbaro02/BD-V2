# Architecture Status

The architecture is defined by the frozen implementation pack and expanded in
the development plan. The implemented modular monolith now includes FastAPI,
deterministic policies and workflow services, PostgreSQL revision/audit and
idempotency persistence, and five bounded OpenAI Agents SDK specialists invoked
through an application-owned runner boundary.

No external action integration is present. The orchestrator owns sequencing,
exact-current dependency checks, scoped holds, persistence, and reassessment; it
does not author commercial judgments or Human Authorization.

