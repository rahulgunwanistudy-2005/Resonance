from pydantic import ValidationError

from resonance.agent.policy import Proposal


def validate_proposal(payload: str | None, allowed: set[str]) -> tuple[Proposal | None, str]:
    if payload is None:
        return None, "Deterministic policy; no language-model planner configured"
    try:
        proposal = Proposal.model_validate_json(payload)
    except ValidationError:
        return None, "Discarded malformed or unrecognized planner proposal"
    if proposal.tool not in allowed:
        return None, "Discarded proposal outside the current policy whitelist"
    return proposal, "Validated proposal; deterministic evidence gates still apply"
