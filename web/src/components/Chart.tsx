import { useEffect, useRef, useState } from "react";
import { numberText } from "../display";
import uPlot from "uplot";
export function Chart({
  title,
  x,
  y,
  xLabel,
  yLabel,
  color = "#3DE0D0",
}: {
  title: string;
  color?: string;
  x: number[];
  y: number[];
  xLabel: string;
  yLabel: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [table, setTable] = useState(false);
  useEffect(() => {
    if (!ref.current || !x.length) return;
    const root = ref.current;
    const plot = new uPlot(
      {
        width: Math.max(240, root.clientWidth),
        height: 200,
        scales: { x: { time: false } },
        series: [{}, { label: yLabel, stroke: color, width: 1.5 }],
        axes: [
          {
            label: xLabel,
            font: "12px Manrope",
            labelFont: "12px Manrope",
            stroke: "#A9B6CE",
            grid: { stroke: "rgba(160,180,230,0.12)" },
            ticks: { stroke: "rgba(160,180,230,0.25)" },
          },
          {
            font: "12px Manrope",
            stroke: "#A9B6CE",
            grid: { stroke: "rgba(160,180,230,0.12)" },
            ticks: { stroke: "rgba(160,180,230,0.25)" },
          },
        ],
        legend: { show: false },
        cursor: { show: true },
      },
      [x, y],
      root,
    );
    const observer = new ResizeObserver(() =>
      plot.setSize({ width: Math.max(240, root.clientWidth), height: 200 }),
    );
    observer.observe(root);
    return () => {
      observer.disconnect();
      plot.destroy();
    };
  }, [x, y, xLabel, yLabel, color]);
  return (
    <section className="chart">
      <div className="section-title">
        <h3>{title}</h3>
        <button
          className="quiet"
          aria-expanded={table}
          onClick={() => setTable(!table)}
        >
          {table ? "Hide numeric table" : "Show numeric table"}
        </button>
      </div>
      <div
        ref={ref}
        role="img"
        aria-label={`${title}. Numeric samples are available in the table.`}
      />
      {table && (
        <div className="table-scroll" tabIndex={0}>
          <table>
            <caption>{title} samples</caption>
            <thead>
              <tr>
                <th>{xLabel}</th>
                <th>{yLabel}</th>
              </tr>
            </thead>
            <tbody>
              {x.map((value, index) => (
                <tr key={index}>
                  <td>{value.toFixed(3)}</td>
                  <td>{numberText(y[index], 5, "Sample not recorded")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
