"""MCP stdio boundary. Start with PYTHONPATH=. so the app and installed MCP SDK resolve."""

from mcp.server.fastmcp import FastMCP

from api.app.schemas import (
    ApprovalRecord,
    BridgeCreate,
    CaptureCreate,
    CaptureRecord,
    DomainError,
)
from api.app.services.catalog import Catalog
from resonance.agent.policy import Policy
from resonance.config import Settings
from resonance.pipeline import measure as measure_video

server = FastMCP("Resonance")


def catalog() -> Catalog:
    return Catalog(Settings.from_env())


@server.tool()
def enroll(bridge: BridgeCreate) -> str:
    """Enroll bridge geometry and the engineering frequency prior."""
    return catalog().create_bridge(bridge).model_dump_json()


@server.tool()
def capture(request: CaptureCreate) -> str:
    """Create a bounded upload ticket; this does not control an unconfigured remote camera."""
    return catalog().create_capture(request, "mcp-local").model_dump_json()


@server.tool()
def measure(capture_id: str) -> str:
    """Execute the actual OpenCV engine on an existing uploaded capture."""
    service = catalog()
    record = service.store.get("capture", capture_id, CaptureRecord)
    return measure_video(record.capture, settings=service.settings).model_dump_json()


@server.tool()
def compare(capture_id: str) -> str:
    """Read the persisted baseline assessment and the evidence-driven agent trace."""
    record = catalog().store.get("capture", capture_id, CaptureRecord)
    if record.result is None:
        raise DomainError("Capture has not been processed")
    return record.result.model_dump_json()


@server.tool()
def set_policy(bridge_id: str, policy: Policy) -> str:
    """Store a schema-validated deterministic policy. Approval cannot be disabled."""
    service = catalog()
    service.store.put("policy", bridge_id, policy, bridge_id)
    return policy.model_dump_json()


@server.tool()
def request_approval(capture_id: str) -> str:
    """Return the human-review request created by an actual ALERT decision."""
    service = catalog()
    record = service.store.get("capture", capture_id, CaptureRecord)
    if record.result is None or record.result.decision.approval_id is None:
        raise DomainError(
            "No evidence-backed inspection request exists for this capture"
        )
    return service.store.get(
        "approval", record.result.decision.approval_id, ApprovalRecord
    ).model_dump_json()


@server.tool()
def run_bench() -> str:
    """Run the reproducible local benchmark; no cloud capacity or price is inferred."""
    from bench.run_bench import run
    import json

    return json.dumps(run())


if __name__ == "__main__":
    server.run(transport="stdio")
