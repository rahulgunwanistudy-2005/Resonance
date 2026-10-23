"""Planned integration seams. Protocols are contracts, not implemented features."""

from pathlib import Path
from typing import Protocol

from resonance.models import Capture, Decision, ModalEstimate, TraceEvent


class MeasurementTool(Protocol):
    def __call__(self, capture: Capture) -> ModalEstimate: ...


class EvidenceStore(Protocol):
    def put(self, path: Path, *, capture_id: str) -> str: ...


class TraceStore(Protocol):
    def append(self, event: TraceEvent) -> None: ...


class ApprovalNotifier(Protocol):
    def send_approved(self, decision: Decision, *, approval_id: str) -> str: ...
