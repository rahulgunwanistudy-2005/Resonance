import type { Trace } from "../types";
export function Timeline({ events }: { events: Trace[] }) {
  return (
    <ol className="timeline">
      {events.map((event, index) => (
        <li key={`${event.ts}-${index}`}>
          <div className="timeline-head">
            <strong>{event.state.toLowerCase().replaceAll("_", " ")}</strong>
            <span>{event.action.replaceAll("_", " ")}</span>
          </div>
          <p>{event.decision}</p>
          <small>{event.outcome.replaceAll("_", " ")}</small>
          {event.proposal && (
            <details>
              <summary>Planner proposal</summary>
              <pre>{event.proposal}</pre>
            </details>
          )}
        </li>
      ))}
    </ol>
  );
}
