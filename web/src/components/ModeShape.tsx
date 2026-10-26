import type { Fdd, Roi } from "../types";

// Plots the measured FDD mode shape; regions are placed by their horizontal centre in the frame.
export function ModeShape({
  fdd,
  rois,
  color,
}: {
  fdd: Fdd;
  rois: Roi[];
  color: string;
}) {
  const centre = (id: string) => {
    const roi = rois.find((r) => r.id === id);
    return roi ? roi.x + roi.width / 2 : 0;
  };
  const scale = Math.max(...fdd.mode_shape_real.map(Math.abs)) || 1;
  const points = fdd.roi_ids
    .map((id, i) => ({
      id,
      x: centre(id),
      value: fdd.mode_shape_real[i] / scale,
    }))
    .sort((a, b) => a.x - b.x);
  const xs = points.map((p) => p.x);
  const low = Math.min(...xs);
  const span = Math.max(...xs) - low || 1;
  const W = 720,
    H = 230,
    left = 50,
    right = 680,
    mid = 115,
    amp = 85;
  const at = (p: (typeof points)[number], i: number) => ({
    cx:
      points.length > 1 && span > 1
        ? left + ((p.x - low) / span) * (right - left)
        : left + (i / Math.max(1, points.length - 1)) * (right - left),
    cy: mid - p.value * amp,
  });
  const placed = points.map(at);
  return (
    <section className="chart">
      <div className="section-title">
        <h3>Mode shape</h3>
        <span className="mode-note">
          Frequency-domain decomposition near {fdd.peak_bin_hz.toFixed(3)} Hz
        </span>
      </div>
      <svg
        className="mode-shape"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Normalised first mode shape across the measured regions. Values are listed in the table below."
      >
        <line x1={left} y1={mid} x2={right} y2={mid} className="axis" />
        <line
          x1={left}
          y1={mid - amp}
          x2={right}
          y2={mid - amp}
          className="grid"
        />
        <line
          x1={left}
          y1={mid + amp}
          x2={right}
          y2={mid + amp}
          className="grid"
        />
        <text x={left - 8} y={mid - amp + 4} textAnchor="end">
          +1
        </text>
        <text x={left - 8} y={mid + 4} textAnchor="end">
          0
        </text>
        <text x={left - 8} y={mid + amp + 4} textAnchor="end">
          −1
        </text>
        <path
          d={"M" + placed.map((p) => `${p.cx} ${p.cy}`).join(" L")}
          fill="none"
          stroke={color}
          strokeWidth="2.4"
        />
        {placed.map((p, i) => (
          <g key={points[i].id}>
            <circle cx={p.cx} cy={p.cy} r="5" fill={color} />
            <text x={p.cx} y={H - 4} textAnchor="middle">
              {points[i].id}
            </text>
          </g>
        ))}
      </svg>
      <div className="table-scroll" tabIndex={0}>
        <table>
          <caption>Mode shape values, left to right in the frame</caption>
          <thead>
            <tr>
              <th>Region</th>
              <th>Normalised real part</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.id}>
                <th>{p.id}</th>
                <td>{p.value.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
