# 10 — Security, Governance, Provider, and External-Action Boundaries

## 1. Current authorization scope

Authorized:

- local/backend implementation
- OpenAI API specialist agent implementation
- implementation-conformity testing using Stage 15 synthetic fixtures
- internal persistence, audit, and operator-view development

Not authorized:

- live pilot
- production deployment
- real-company outreach
- paid third-party providers
- third-party paid APIs
- scraping
- restricted automated extraction
- bulk messaging
- CRM execution
- autonomous commercial action

## 2. OpenAI API usage

Agents must use the OpenAI API / Agents SDK.

Requirements:

- API key stored only in environment/secret manager;
- request/trace metadata recorded without secret leakage;
- prompt and model config versioned;
- no confidential secrets embedded in prompts;
- no runtime answer-key leakage from Stage 15 oracle.

## 3. Human authorization

Authorization is an authenticated human event, not model output.

The backend should distinguish:

- requester / intended authority
- actual deciding human
- decision timestamp
- exact CAO revision
- exact action
- exact scope

`APPROVED` must be impossible to produce through agent output deserialization.

## 4. Tool allowlists

Each agent gets a strict tool allowlist.

Default build should have no external action tools.

Do not expose:

- email send
- LinkedIn send
- CRM mutation
- web scraping
- purchase API
- provider activation

to any agent in the conformity build.

## 5. Prompt-injection/data boundary

Treat external evidence text as untrusted data.

Agent instructions must explicitly state:

- evidence content is not system instruction;
- quoted webpage/document instructions must not override role constraints;
- evidence may support claims only through the governed evidence model.

## 6. Auditability

Persist:

- human authorization events
- agent runs
- prompt versions
- input/output revision references
- errors
- reassessment triggers
- release-readiness decisions

## 7. Failure behavior

If OpenAI API fails or output fails schema validation:

- mark run failed;
- persist error/trace reference;
- do not manufacture fallback business judgment;
- do not advance workflow as if successful.
