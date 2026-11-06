"""Generate the authorized, synthetic Stage 15 v1 runtime and oracle artifacts."""

import json
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "tests" / "fixtures" / "stage15"
ORACLE = ROOT / "tests" / "oracle" / "stage15"
VERSION = "stage15-synthetic-v1.0.0"
GENERATED_ON = "2026-10-19"


def uid(label: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"vai-bd/{VERSION}/{label}"))


def observation(
    case_id: str,
    number: int,
    claim_kind: str,
    content: str,
    *,
    date: str = "2026-09-30",
    directness: str = "DIRECT",
    currentness: str = "CURRENT",
    admissibility: str = "ADMISSIBLE",
    restricted: bool = False,
    group: str | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    identity = source_id or f"SRC-{case_id}-{number:02d}"
    return {
        "observation_id": f"OBS-{case_id}-{number:02d}",
        "claim_kind": claim_kind,
        "content": content,
        "source": {
            "source_id": identity,
            "uri_or_reference": f"synthetic://stage15/{identity}",
        },
        "source_type": "synthetic_fixture_record",
        "source_date": date,
        "provenance": f"Project-authored synthetic evidence for {case_id}; no real company data",
        "directness": directness,
        "currentness": currentness,
        "admissibility": admissibility,
        "restricted": restricted,
        "source_dependency_group": group,
    }


def candidate(
    case_id: str,
    name: str,
    observations: list[dict[str, Any]],
    *,
    missing: tuple[str, ...] = (),
    demand: str | None = None,
    next_action: str | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "candidate_id": uid(f"candidate/{case_id}"),
        "company_name": name,
        "segment_claim": "Synthetic business-services company",
        "observations": observations,
        "missing_material_facts": list(missing),
        "pursuit_demand_hours": demand,
        "next_action": next_action,
    }


def base_candidates() -> list[dict[str, Any]]:
    shared = "SG-SHARED-MARKET-01"
    return [
        candidate(
            "C01",
            "Synthetic Alder Operations",
            [
                observation(
                    "C01",
                    1,
                    "market_presence",
                    "Operates inside the configured market.",
                    group=shared,
                    source_id="SRC-SHARED-MARKET-01",
                ),
                observation("C01", 2, "fit", "Uses a workflow matched by the configured offer."),
                observation(
                    "C01", 3, "need", "A current operational bottleneck is directly documented."
                ),
                observation(
                    "C01", 4, "decision_owner", "The operations director owns the workflow."
                ),
            ],
            demand="2.0",
            next_action="Prepare a bounded internal evidence brief for human review.",
        ),
        candidate(
            "C02",
            "Synthetic Birch Systems",
            [
                observation(
                    "C02",
                    1,
                    "market_presence",
                    "Operates inside the configured market.",
                    group=shared,
                    source_id="SRC-SHARED-MARKET-01",
                ),
                observation("C02", 2, "fit", "The documented workflow matches the offer."),
                observation(
                    "C02",
                    3,
                    "need",
                    "A need is suggested but not directly confirmed.",
                    directness="INFERENTIAL",
                ),
                observation("C02", 4, "decision_owner", "An operations role is the likely owner."),
            ],
            missing=("Direct confirmation of current Need",),
            demand="1.5",
            next_action="Confirm the current operational Need.",
        ),
        candidate(
            "C03",
            "Synthetic Cedar Connect",
            [
                observation("C03", 1, "market_presence", "Operates inside the configured market."),
                observation(
                    "C03",
                    2,
                    "fit",
                    "Only a moderate workflow match is documented.",
                    directness="INFERENTIAL",
                ),
                observation(
                    "C03",
                    3,
                    "need",
                    "The problem appears occasional rather than persistent.",
                    directness="INFERENTIAL",
                ),
                observation(
                    "C03", 4, "contactability", "Several direct contact paths are documented."
                ),
            ],
            demand="1.0",
            next_action="Validate whether the occasional problem is material.",
        ),
        candidate(
            "C04",
            "Synthetic Dogwood Works",
            [
                observation(
                    "C04",
                    1,
                    "market_presence",
                    "Operates inside the configured market.",
                    group=shared,
                    source_id="SRC-SHARED-MARKET-01",
                ),
                observation("C04", 2, "fit", "The core workflow strongly matches the offer."),
                observation(
                    "C04", 3, "need", "A current high-impact operational need is documented."
                ),
                observation(
                    "C04", 4, "decision_owner", "A transformation lead owns the initiative."
                ),
                observation("C04", 5, "effort", "A credible first action requires three hours."),
            ],
            demand="3.0",
            next_action="Prepare the high-effort evidence package for review.",
        ),
        candidate(
            "C05",
            "Synthetic Elm Advisory",
            [
                observation("C05", 1, "market_presence", "Operates inside the configured market."),
                observation(
                    "C05",
                    2,
                    "need",
                    "A workflow issue is described by the originating record.",
                    group="SG-ECHO-C05",
                    source_id="SRC-C05-ORIGIN",
                ),
                observation(
                    "C05",
                    3,
                    "need",
                    "A second record repeats the originating workflow claim.",
                    group="SG-ECHO-C05",
                    source_id="SRC-C05-ECHO",
                ),
                observation("C05", 4, "fit", "The described workflow matches the offer."),
            ],
            demand="1.0",
            next_action="Seek an independent source for the echoed Need claim.",
        ),
        candidate(
            "C06",
            "Synthetic Fir Logistics",
            [
                observation("C06", 1, "market_presence", "Operates inside the configured market."),
                observation(
                    "C06", 2, "market_presence", "Operates only outside the configured market."
                ),
                observation("C06", 3, "fit", "The operating model could match the offer."),
            ],
            missing=("Resolution of the material market-presence contradiction",),
            next_action="Resolve the contradictory market-presence records.",
        ),
        candidate(
            "C07",
            "Synthetic Grove Studio",
            [
                observation(
                    "C07",
                    1,
                    "market_presence",
                    "May operate in the configured market.",
                    directness="INFERENTIAL",
                    currentness="UNKNOWN",
                    admissibility="UNKNOWN",
                ),
            ],
            missing=("Admissible market presence", "Fit", "Need", "Decision owner"),
            next_action="Gather minimum admissible evidence.",
        ),
        candidate(
            "C08",
            "Synthetic Harbor Group",
            [
                observation(
                    "C08",
                    1,
                    "market_presence",
                    "Operates exclusively outside the configured market.",
                ),
                observation("C08", 2, "fit", "Its workflow could otherwise match the offer."),
            ],
            next_action="Retain as excluded for this decision cycle.",
        ),
        candidate(
            "C09",
            "Synthetic Indigo Services",
            [
                observation("C09", 1, "market_presence", "Operates inside the configured market."),
                observation("C09", 2, "fit", "The visible workflow matches the offer."),
                observation(
                    "C09",
                    3,
                    "critical_need",
                    "A restricted record claims an urgent active Need.",
                    admissibility="RESTRICTED",
                    restricted=True,
                ),
            ],
            missing=("Admissible confirmation of the critical Need fact",),
            next_action="Investigate the critical Need through an authorized admissible source.",
        ),
        candidate(
            "C10",
            "Synthetic Juniper Labs",
            [
                observation(
                    "C10",
                    1,
                    "market_presence",
                    "Operated inside the configured market in 2023.",
                    date="2023-03-15",
                    currentness="STALE",
                ),
                observation(
                    "C10",
                    2,
                    "fit",
                    "The 2023 workflow matched the offer.",
                    date="2023-03-15",
                    currentness="STALE",
                ),
                observation(
                    "C10",
                    3,
                    "need",
                    "A Need was documented in 2023.",
                    date="2023-03-15",
                    currentness="STALE",
                ),
            ],
            missing=("Current market presence", "Current Need"),
            next_action="Refresh the materially stale evidence before reassessment.",
        ),
    ]


def base_fixture() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "fixture_version": VERSION,
        "synthetic_only": True,
        "configuration": {
            "operator_name": "Synthetic Operator",
            "offer_name": "Workflow Reliability Advisory",
            "problem_statement": (
                "Reduce preventable breakdowns in recurring operational workflows."
            ),
            "intended_buyer_roles": ["Operations Director", "Transformation Lead"],
            "fit_dimensions": ["Recurring workflow", "Operational ownership", "Material friction"],
            "target_market_boundary": "Northern Virginia synthetic business-services segment",
            "segment_filters": ["Business services", "20-500 synthetic employees"],
            "exclusions": ["Outside Northern Virginia", "Consumer-only operations"],
            "effective_date": "2026-10-19",
            "usable_time_hours": "6.0",
            "planning_horizon": "One operating week",
            "max_concurrent_pursuits": 8,
        },
        "candidates": base_candidates(),
    }


def captured_outputs(base: dict[str, Any]) -> dict[str, Any]:
    profile = {
        "C01": ("STRONG", "SUPPORTED", "SUPPORTED", "MEDIUM", "QUALIFIED", ()),
        "C02": (
            "STRONG",
            "PROVISIONAL",
            "ROLE_HYPOTHESIS",
            "MEDIUM",
            "QUALIFIED",
            ("Need lacks direct confirmation",),
        ),
        "C03": (
            "MODERATE",
            "PROVISIONAL",
            "UNRESOLVED",
            "HIGH",
            "QUALIFIED",
            ("Commercial quality remains moderate",),
        ),
        "C04": (
            "STRONG",
            "SUPPORTED",
            "SUPPORTED",
            "MEDIUM",
            "QUALIFIED",
            ("High Pursuit Demand",),
        ),
        "C05": (
            "STRONG",
            "SUPPORTED",
            "UNRESOLVED",
            "LOW",
            "QUALIFIED",
            ("Need evidence shares one dependency group",),
        ),
        "C06": (None, None, None, None, None, ("Material market-presence contradiction",)),
        "C07": (None, None, None, None, None, ("Minimum evidence not satisfied",)),
        "C08": (None, None, None, None, None, ("Outside configured market",)),
        "C09": (
            "STRONG",
            "INSUFFICIENT",
            "UNRESOLVED",
            "LOW",
            "FURTHER_INVESTIGATION_REQUIRED",
            ("Critical fact exists only in a restricted source",),
        ),
        "C10": (
            "INDETERMINATE",
            "INSUFFICIENT",
            "UNRESOLVED",
            "LOW",
            "FURTHER_INVESTIGATION_REQUIRED",
            ("Material evidence is stale",),
        ),
    }
    gate = {
        "C01": (True, False, False, True),
        "C02": (True, False, False, True),
        "C03": (True, False, False, True),
        "C04": (True, False, False, True),
        "C05": (True, False, False, True),
        "C06": (True, True, False, True),
        "C07": (True, False, False, False),
        "C08": (True, False, True, True),
        "C09": (True, False, False, True),
        "C10": (True, False, False, True),
    }
    cases = []
    for item in base["candidates"]:
        case_id = item["case_id"]
        fit, need, owner, contact, qualification, uncertainties = profile[case_id]
        boundary, contradiction, exclusion, minimum = gate[case_id]
        cases.append(
            {
                "case_id": case_id,
                "referenced_observation_ids": [
                    obs["observation_id"] for obs in item["observations"]
                ],
                "missing_evidence_flags": item["missing_material_facts"],
                "gate_facts": {
                    "market_boundary_valid": boundary,
                    "material_contradiction": contradiction,
                    "known_hard_exclusion": exclusion,
                    "minimum_evidence_satisfied": minimum,
                },
                "fit_judgment": fit,
                "need_status": need,
                "decision_owner_status": owner,
                "contactability": contact,
                "qualification": qualification,
                "material_uncertainties": list(uncertainties),
            }
        )
    order = ["C01", "C04", "C02", "C05", "C03"]
    pairs = [[higher, lower, "ABOVE"] for higher, lower in combinations(order, 2)]
    return {
        "schema_version": "1.0",
        "fixture_version": VERSION,
        "cases": cases,
        "portfolio": {
            "snapshot_members": ["C01", "C02", "C03", "C04", "C05"],
            "comparison_order": order,
            "pairwise_relations": pairs,
            "allocation": {
                "ACT_NOW": ["C01", "C04", "C05"],
                "DEFERRED_CAPACITY": ["C02"],
                "DEFERRED_PRIORITY": ["C03"],
                "INVESTIGATE": [],
            },
        },
    }


def mutation_payloads() -> dict[str, dict[str, Any]]:
    c12 = candidate(
        "C12",
        "Synthetic Keystone Partners",
        [
            observation("C12", 1, "market_presence", "Operates inside the configured market."),
            observation("C12", 2, "fit", "The core workflow strongly matches the offer."),
            observation("C12", 3, "need", "A current material Need is directly documented."),
            observation("C12", 4, "decision_owner", "An operations executive owns the workflow."),
        ],
        demand="2.0",
        next_action="Prepare a bounded internal evidence brief for review.",
    )
    definitions = {
        "M01": ("Capacity drop to four hours", {"replace_capacity_hours": "4.0"}),
        "M02": (
            "New qualified candidate C12",
            {
                "add_candidate": c12,
                "new_universe_revision": 2,
                "new_snapshot_revision": 2,
                "captured_comparison_order": [
                    "C01",
                    "C12",
                    "C04",
                    "C02",
                    "C05",
                    "C03",
                ],
            },
        ),
        "M03": (
            "Material comparison cycle",
            {
                "replace_comparisons": [
                    ["C01", "C04", "ABOVE"],
                    ["C04", "C02", "ABOVE"],
                    ["C02", "C01", "ABOVE"],
                ]
            },
        ),
        "M04": (
            "Authorized action supersession",
            {
                "cao_identity": uid("mutation/M04/cao"),
                "approved_revision": 1,
                "superseding_revision": 2,
                "material_change": "Action scope changed",
            },
        ),
        "M05": (
            "Human review non-response",
            {"authorization_state": "PENDING_HUMAN_REVIEW", "timeout_elapsed": True},
        ),
        "M06": ("Missing capacity envelope", {"remove_capacity_envelope": True}),
        "M07": ("Missing governing market boundary", {"target_market_boundary": None}),
        "M08": (
            "Shared source becomes unreliable",
            {
                "unreliable_source_dependency_group": "SG-SHARED-MARKET-01",
                "directly_affected_cases": ["C01", "C02", "C04"],
            },
        ),
        "M09": (
            "Missing decision owner",
            {"case_id": "C01", "remove_claim_kind": "decision_owner"},
        ),
    }
    return {
        key: {
            "schema_version": "1.0",
            "fixture_version": VERSION,
            "mutation_id": key,
            "title": title,
            "base_fixture_version": VERSION,
            "changes": changes,
        }
        for key, (title, changes) in definitions.items()
    }


def oracle_base() -> dict[str, Any]:
    order = ["C01", "C04", "C02", "C05", "C03"]
    return {
        "schema_version": "1.0",
        "fixture_version": VERSION,
        "case_expectations": {
            "C01": {"gate": "PROCEED", "qualification": "QUALIFIED"},
            "C02": {"gate": "PROCEED", "qualification": "QUALIFIED", "need": "PROVISIONAL"},
            "C03": {
                "gate": "PROCEED",
                "qualification": "QUALIFIED",
                "constraint": "contactability_does_not_raise_priority",
            },
            "C04": {
                "gate": "PROCEED",
                "qualification": "QUALIFIED",
                "constraint": "demand_does_not_reduce_quality",
            },
            "C05": {
                "gate": "PROCEED",
                "qualification": "QUALIFIED",
                "limitation": "source_dependency_disclosed",
            },
            "C06": {
                "gate": "CONTRADICTION_BLOCK",
                "qualification": "INDETERMINATE_PENDING_MATERIAL_REVIEW",
            },
            "C07": {"gate": "EVIDENCE_REQUIRED", "substantive_assessment": False},
            "C08": {"gate": "HARD_EXCLUSION", "scope": "LOCAL"},
            "C09": {
                "qualification": "FURTHER_INVESTIGATION_REQUIRED",
                "restricted_fact_consumed": False,
            },
            "C10": {
                "qualification": "FURTHER_INVESTIGATION_REQUIRED",
                "reassessment_required": True,
            },
        },
        "snapshot_members": ["C01", "C02", "C03", "C04", "C05"],
        "comparison_order": order,
        "pairwise_relations": [[a, b, "ABOVE"] for a, b in combinations(order, 2)],
        "pursuit_demand_hours": {
            "C01": "2.0",
            "C04": "3.0",
            "C02": "1.5",
            "C05": "1.0",
            "C03": "1.0",
        },
        "allocation": {
            "ACT_NOW": ["C01", "C04", "C05"],
            "DEFERRED_CAPACITY": ["C02"],
            "DEFERRED_PRIORITY": ["C03"],
            "INVESTIGATE": [],
        },
        "material_invariants": [
            "priority:C02>C05",
            "allocation:C05_may_use_residual_capacity",
            "all_unresolved_candidates_explicit",
        ],
        "expected_rule_refs": [
            "stage15-base-cases",
            "minimum-evidence-precedence",
            "pairwise-completeness",
            "capacity-feasibility",
        ],
    }


def oracle_mutations() -> dict[str, dict[str, Any]]:
    expected = {
        "M01": {
            "allocation": {"ACT_NOW": ["C01", "C02"], "DEFERRED_CAPACITY": ["C04"]},
            "priority_unchanged": True,
        },
        "M02": {
            "comparison_order": ["C01", "C12", "C04", "C02", "C05", "C03"],
            "allocation": {"ACT_NOW": ["C01", "C12", "C02"], "DEFERRED_CAPACITY": ["C04"]},
            "historical_snapshot_unchanged": True,
        },
        "M03": {"cycle_exposed": True, "forced_total_order": False, "allocation_held": True},
        "M04": {
            "revision_1_history_retained": True,
            "revision_2_authorized": False,
            "revision_1_new_execution_eligible": False,
        },
        "M05": {"authorization_state": "PENDING_HUMAN_REVIEW", "authorized": False},
        "M06": {
            "capacity_independent_work_allowed": True,
            "allocation_exists": False,
            "act_now": [],
        },
        "M07": {
            "cycle_state": "HELD",
            "geographic_eligibility_created": False,
            "priority_created": False,
        },
        "M08": {
            "reassessment_cases": ["C01", "C02", "C04"],
            "unaffected_cases_current": ["C03", "C05", "C06", "C07", "C08", "C09", "C10"],
        },
        "M09": {
            "fit_unchanged": True,
            "need_unchanged": True,
            "decision_owner": "UNRESOLVED",
            "next_action_type": "EVIDENCE_GATHERING",
        },
    }
    return {
        key: {
            "schema_version": "1.0",
            "fixture_version": VERSION,
            "mutation_id": key,
            "expected": value,
            "expected_rule_refs": [f"stage15-{key.lower()}", "governed-concept-separation"],
        }
        for key, value in expected.items()
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    base = base_fixture()
    outputs = captured_outputs(base)
    write_json(RUNTIME / "base.json", base)
    write_json(RUNTIME / "captured_outputs.json", outputs)
    mutations = mutation_payloads()
    for mutation_id, payload in mutations.items():
        write_json(RUNTIME / "mutations" / f"{mutation_id}.json", payload)
    runtime_paths = [Path("base.json"), Path("captured_outputs.json")]
    runtime_paths.extend(Path("mutations") / f"M{number:02d}.json" for number in range(1, 10))
    runtime_manifest = {
        "schema_version": "1.0",
        "fixture_version": VERSION,
        "generated_on": GENERATED_ON,
        "authorization": "Generated at the user's explicit request on 2026-10-19",
        "synthetic_only": True,
        "source_specification": [
            "vai_bd_implementation_pack/08_STAGE15_CONFORMITY_TEST_PLAN.md",
            "vai_bd_development_plan/07_TEST_AND_CONFORMITY_PLAN.md",
        ],
        "files": [{"path": str(path), "sha256": digest(RUNTIME / path)} for path in runtime_paths],
    }
    write_json(RUNTIME / "manifest.json", runtime_manifest)

    write_json(ORACLE / "base_expected.json", oracle_base())
    oracle_mutation_payloads = oracle_mutations()
    for mutation_id, payload in oracle_mutation_payloads.items():
        write_json(ORACLE / "mutations" / f"{mutation_id}.json", payload)
    oracle_paths = [Path("base_expected.json")]
    oracle_paths.extend(Path("mutations") / f"M{number:02d}.json" for number in range(1, 10))
    oracle_manifest = {
        "schema_version": "1.0",
        "fixture_version": VERSION,
        "generated_on": GENERATED_ON,
        "runtime_manifest_sha256": digest(RUNTIME / "manifest.json"),
        "files": [{"path": str(path), "sha256": digest(ORACLE / path)} for path in oracle_paths],
    }
    write_json(ORACLE / "manifest.json", oracle_manifest)
    print(f"generated {VERSION}: 10 base cases, 9 mutations, separated oracle")


if __name__ == "__main__":
    main()
