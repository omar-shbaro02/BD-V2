# Security, Operations, and Evidence Package

## 1. Secrets and configuration

- Load secrets only from environment/approved secret storage.
- Commit `.env.example`, never `.env` or credentials.
- Redact authorization headers, API keys, raw provider failures, and restricted
  evidence from logs.
- Fail startup when required local-live secrets are missing; offline tests use no
  OpenAI key.
- Treat model, prompt, policy, configuration, and fixture versions as audit data.

## 2. Data and prompt security

External evidence is untrusted data. Delimit it, retain provenance, and prevent it
from selecting tools or overriding instructions. Use strict agent tool allowlists;
the conformity build contains no web, email, social, CRM, purchase, provider
activation, shell, or external mutation tool.

Trace payloads may contain model inputs/outputs. Synthetic conformity data may be
traced; for later non-synthetic use, disable sensitive trace content by default
and document retention/access rules before any pilot authorization.

## 3. Authentication and authorization

The local test adapter exists only to prove the application boundary. It must:

- verify a signed principal;
- produce server-owned actor ID and actor kind;
- reject missing/expired/invalid identity;
- prevent request bodies from overriding the actual deciding human.

Before any future deployment, replace it with an approved identity provider and
repeat authorization/API tests. That replacement is outside this build.

## 4. Audit and failure behavior

Persist agent runs, input/output refs, prompt/model versions, trace refs, errors,
workflow transitions, materiality decisions, release checks, authorization
events, and execution-eligibility decisions.

On DB, model, validation, or policy failure:

1. roll back incomplete governed writes;
2. mark the run failed when possible;
3. persist a sanitized error/audit reference;
4. leave downstream state unadvanced;
5. return an actionable held/failed response;
6. never manufacture a fallback commercial judgment.

## 5. Local operating procedure

The root README must document:

1. prerequisites and exact supported Python/PostgreSQL versions;
2. dependency installation from lock file;
3. environment creation without real secrets for offline mode;
4. database start and migration;
5. unit/integration/conformity commands;
6. local API/operator-view start;
7. optional authorized synthetic live-agent smoke command;
8. evidence-package generation;
9. cleanup that does not delete governed data accidentally.

No deployment instructions or production credentials belong in v0.1.

## 6. Evidence Package v0.1 contents

Generate a manifest with SHA-256 digests and include:

- exact VCS commit/version and dirty-state indication;
- repository tree and source-pack/development-plan versions;
- setup, migration, run, and test instructions;
- dependency lock digest and Alembic head;
- architecture and service-boundary map;
- five-agent responsibility, prompt version/digest, model config, and tool inventory;
- complete domain-to-code-to-test traceability matrix;
- Stage 15 fixture and oracle manifests/locations;
- conformity report for every C/M case and negative authority suite;
- failed/skipped tests (material skips must prevent PASS);
- trace/log/audit references without secrets;
- known limitations and exact remaining gaps;
- explicit statements that live pilot, deployment, providers, and external actions
  remain unauthorized.

## 7. Final acceptance checklist

- [x] All frozen distinctions have separate models and visible presentation.
- [x] All governed objects preserve history and exact dependencies.
- [x] All five and only five specialist agents have typed bounded outputs.
- [x] Orchestrator behavior is deterministic and non-substantive.
- [x] Stage 15 oracle is inaccessible to runtime reasoning.
- [x] C01–C10 and M01–M09 pass with no material skip.
- [x] Human Authorization can originate only from authenticated human events.
- [x] External execution evaluates false in the conformity build.
- [x] Operator view separates Priority, Allocation, Readiness, and Authorization.
- [x] Evidence Package is complete, reproducible, and candid about limitations.

Passing this checklist authorizes only the implementation-conformity handoff. It
does not authorize Stage 19, deployment, a live pilot, or external execution.


Phase 12 evidence: `evidence_package/generated/summary.json`,
`traceability.json`, `verification/tests.xml`, and
`verification/conformity-report.json`. The manifest binds every exported file.
