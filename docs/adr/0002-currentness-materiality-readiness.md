# ADR 0002: Currentness, materiality, and release readiness

- Status: Proposed pending governance confirmation
- Date: 2026-10-09

## Decision

- Evidence currentness is evaluated by a versioned, configurable source-type
  policy with explicit as-of dates; there is no universal hidden cutoff.
- Material impact is an auditable rule or human decision. Unknown impact defaults
  to review, never “unaffected.”
- Release readiness uses a versioned checklist of current dependencies,
  represented contradictions/limitations, complete action data, and defensible
  allocation where relevant.

Release readiness remains independent from Human Authorization.

