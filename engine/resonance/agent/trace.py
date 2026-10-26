from pathlib import Path

from resonance.models import TraceEvent


def write_trace(path: Path, events: list[TraceEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text("".join(event.model_dump_json() + "\n" for event in events))
    temporary.replace(path)
