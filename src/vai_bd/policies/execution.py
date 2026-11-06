"""Exact-scope external execution eligibility; never a stored editable flag."""

from collections.abc import Mapping
from dataclasses import dataclass

from vai_bd.domain.actions import ActionScope, CommercialActionOpportunity
from vai_bd.domain.authorization import HumanAuthorizationEvent
from vai_bd.domain.enums import ActorKind, HumanAuthorizationState, ObjectValidity
from vai_bd.domain.refs import ObjectRevisionRef


@dataclass(frozen=True)
class ExternalActionRestriction:
    allows_external_execution: bool
    reason: str


@dataclass(frozen=True)
class ExecutionEligibilityDecision:
    eligible: bool
    reasons: tuple[str, ...]


def evaluate_execution_eligibility(
    cao: CommercialActionOpportunity,
    authorization: HumanAuthorizationEvent | None,
    requested_action: str,
    requested_scope: ActionScope,
    dependency_validities: Mapping[ObjectRevisionRef, ObjectValidity],
    restriction: ExternalActionRestriction,
) -> ExecutionEligibilityDecision:
    reasons: list[str] = []
    if cao.validity is not ObjectValidity.CURRENT:
        reasons.append(f"cao_not_current:{cao.validity.value}")
    if requested_action != cao.action_description:
        reasons.append("requested_action_does_not_match_cao")
    if requested_scope != cao.action_scope:
        reasons.append("requested_scope_does_not_match_cao")
    for ref in cao.dependencies:
        validity = dependency_validities.get(ref)
        if validity is None:
            reasons.append(f"execution_dependency_missing:{_label(ref)}")
        elif validity is not ObjectValidity.CURRENT:
            reasons.append(f"execution_dependency_not_current:{_label(ref)}:{validity.value}")
    if authorization is None:
        reasons.append("approved_authorization_missing")
    else:
        if authorization.state is not HumanAuthorizationState.APPROVED:
            reasons.append("authorization_not_approved")
        if authorization.cao_revision_ref != cao.revision_ref:
            reasons.append("authorization_cao_revision_mismatch")
        if authorization.authorized_action != requested_action:
            reasons.append("authorized_action_mismatch")
        if authorization.authorized_scope != requested_scope:
            reasons.append("authorized_scope_mismatch")
        actor = authorization.actual_deciding_human_ref
        if actor is None or actor.actor_kind is not ActorKind.HUMAN:
            reasons.append("actual_deciding_actor_not_human")
        if authorization.decision_timestamp is None:
            reasons.append("authorization_decision_timestamp_missing")
    if not restriction.allows_external_execution:
        reasons.append(f"external_execution_restricted:{restriction.reason}")
    return ExecutionEligibilityDecision(not reasons, tuple(reasons))


def conformity_restriction() -> ExternalActionRestriction:
    return ExternalActionRestriction(False, "conformity_profile_forbids_external_execution")


def _label(ref: ObjectRevisionRef) -> str:
    return f"{ref.object_type}:{ref.object_id}:r{ref.revision}"
