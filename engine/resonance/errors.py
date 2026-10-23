"""Expected input and evidence failures are explicit, never successful empty results."""


class EvidenceError(ValueError):
    """Input cannot support the requested measurement."""


class CapabilityUnavailable(RuntimeError):
    """An optional capability has not been verified on this runtime."""
