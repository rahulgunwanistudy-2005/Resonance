import type { Trace } from "../types";
const show = (value: string | number | boolean | null) =>
  typeof value === "number"
    ? value.toLocaleString(undefined, { maximumFractionDigits: 4 })
    : String(value);
export function Timeline({ events }: { events: Trace[] }) {
  return (
    <ol className="timeline">
      {events.map((event, index) => {
        const evidence = Object.entries(event.evidence ?? {});
        return (
          <li key={`${event.ts}-${index}`}>
            <div className="timeline-head">
              <span className="step-index">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="outcome">
                {event.outcome.replaceAll("_", " ")}
              </span>
            </div>
            <strong>{event.state.toLowerCase().replaceAll("_", " ")}</strong>
            <p>{event.decision}</p>
            <small>{event.action.replaceAll("_", " ")}</small>
            {evidence.length > 0 && (
              <details>
                <summary>Evidence</summary>
                <dl>
                  {evidence.map(([key, value]) => (
                    <div key={key}>
                      <dt>{key.replaceAll("_", " ")}</dt>
                      <dd>{show(value)}</dd>
                    </div>
                  ))}
                </dl>
              </details>
            )}
            {event.proposal && (
              <details>
                <summary>Planner proposal</summary>
                <pre>{event.proposal}</pre>
              </details>
            )}
          </li>
        );
      })}
    </ol>
  );
}
