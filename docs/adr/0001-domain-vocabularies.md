# ADR 0001: Governed qualitative vocabularies

- Status: Proposed pending governance confirmation
- Date: 2026-10-09

## Context

The frozen schema names several qualitative fields without fixing every enum.
Code needs closed vocabularies without introducing scores.

## Decision

Preserve source-defined enums exactly. Proposed additions are qualitative only:

- Fit judgment: `STRONG`, `MODERATE`, `WEAK`, `INDETERMINATE`.
- Contactability: `HIGH`, `MEDIUM`, `LOW`, `INDETERMINATE`.
- Coverage: `PARTIAL`, `SUFFICIENT_FOR_CYCLE`, `INDETERMINATE`.
- Confidence remains `HIGH`, `MEDIUM`, `LOW`, `INDETERMINATE` and attaches to a
  specific claim with rationale and evidence refs.

These labels do not imply Need, commercial value, Priority, or Allocation.

## Consequences

Do not implement these proposed additions as accepted governed enums until their
meaning is reviewed. Unknown values fail validation rather than map to a score.

