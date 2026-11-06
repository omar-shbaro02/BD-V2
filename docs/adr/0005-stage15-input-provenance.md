# ADR 0005: Stage 15 fixture provenance and synthetic baseline

- Status: Accepted
- Date: 2026-10-19

## Context

The implementation pack supplies the C01–C10 and M01–M09 expected-behavior
summary, but it does not contain the complete frozen synthetic input records.

## Decision

The user explicitly requested generation of the dataset on 2026-10-19. Authorize
`stage15-synthetic-v1.0.0`, a fully fictional baseline constructed from the
documented scenario meanings for C01–C10 and mutations M01–M09.

The generated runtime fixtures and held-out oracle are versioned separately,
digest-bound, and reproducible from `scripts/generate_stage15_dataset.py`. This
baseline is not represented as the missing original frozen artifact. Any future
arrival of that artifact requires a new version and provenance decision rather
than silent replacement.

