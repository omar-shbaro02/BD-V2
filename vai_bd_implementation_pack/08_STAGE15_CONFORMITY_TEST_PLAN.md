# 08 — Stage 15 Conformity Test Plan

The frozen Stage 15 Synthetic Dataset is the design-level answer key. Runtime fixtures must expose only synthetic inputs. Expected adjudications must remain held out.

## 1. Required base candidates

- C01 — strong Fit + current supporting Need evidence
- C02 — strong Fit + weak direct Need
- C03 — moderate commercial case + high Contactability
- C04 — strong case + high Pursuit Demand
- C05 — source echo / dependent evidence
- C06 — material contradiction in market presence
- C07 — insufficient minimum evidence
- C08 — outside target-market boundary
- C09 — critical missing fact only in unauthorized/restricted source
- C10 — materially stale evidence

## 2. Base expected qualification behavior

- C01: Qualified
- C02: Qualified; Need provisional
- C03: Qualified; contactability does not elevate over stronger commercial cases
- C04: Qualified
- C05: Qualified with source-dependence limitation
- C06: gate blocked; downstream Indeterminate pending review
- C07: evidence required; no substantive qualification
- C08: hard exclusion for this cycle
- C09: Further Investigation Required; restricted source not silently used
- C10: Further Investigation / Reassessment Required due staleness

## 3. Base qualified universe

Snapshot includes:

- C01
- C02
- C03
- C04
- C05

Unresolved/excluded candidates remain explicitly represented outside the comparison set.

## 4. Base comparative order

Dataset answer key:

```text
C01 > C04 > C02 > C05 > C03
```

All 10 unique pairwise relations for five opportunities must exist once.

## 5. Base Pursuit Demand

- C01: 2.0h
- C04: 3.0h
- C02: 1.5h
- C05: 1.0h
- C03: 1.0h

Base capacity: 6h.

Expected allocation:

- Act Now: C01, C04, C05
- Deferred — Capacity: C02
- Deferred — Lower Priority: C03

Critical assertion:

`priority(C02) > priority(C05)` while `C05` may be Act Now due residual capacity.

## 6. Required mutations

### M01 — capacity drop to 4h

Expected:

- C01 Act Now
- C04 deferred due capacity
- C02 Act Now
- commercial priority unchanged

### M02 — new candidate C12

Create a new Candidate Universe / Qualified Universe Snapshot revision.

Expected order:

```text
C01 > C12 > C04 > C02 > C05 > C03
```

With 6h and C12=2h:

- C01 Act Now
- C12 Act Now
- C04 cannot fit
- C02 Act Now

Historical snapshot must remain unchanged.

### M03 — comparison cycle

```text
A > B
B > C
C > A
```

Expected:

- cycle exposed
- Comparative Priority may be Indeterminate
- no forced total ranking
- allocation held if material

### M04 — authorization revision/supersession

- R1 Approved
- material change produces R2 superseding R1

Expected:

- R1 approval does not authorize R2
- historical R1 approval remains auditable
- superseded R1 not eligible for new execution based solely on old approval

### M05 — non-response

Pending Human Review + timeout.

Expected:

- remains non-authorized
- may trigger urgency/escalation/reassessment

### M06 — missing Capacity Envelope

Expected:

- capacity-independent work may continue
- no valid allocation / Act Now portfolio
- capacity cannot be invented

### M07 — missing market boundary

Expected:

- cycle held
- no geographic eligibility or market-relative priority claims

### M08 — shared source becomes unreliable

Expected:

- propagation across all materially dependent candidates/objects
- unaffected objects remain current

### M09 — missing Decision-Owner

Expected:

- Fit/Need may remain strong
- next action may be targeted decision-owner investigation
- Decision-Owner uncertainty must not rewrite Fit/Need

## 7. Conformity assertions

The test suite MUST detect failure if implementation:

- counts repeated dependent sources as independent evidence;
- treats missing Need as evidence of no Need;
- lets Contactability defeat materially stronger commercial quality;
- changes priority because capacity changes;
- drops unresolved material candidates silently;
- forces a ranking through a comparison cycle;
- consumes restricted evidence without authority;
- invents market/capacity inputs;
- transfers R1 authorization to R2;
- lets superseded R1 execute from historical approval;
- converts silence/timeout to approval;
- lets any agent/Orchestrator create Human Authorization.

## 8. PASS rule

Text does not need to match the answer key verbatim.

The material governed meaning must match.
