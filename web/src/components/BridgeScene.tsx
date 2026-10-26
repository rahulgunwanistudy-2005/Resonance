import { useId, useMemo } from "react";

// Decorative illustration only. Nothing drawn here is a measurement.
type Props = {
  mood?: "dusk" | "night";
  ribbon?: boolean;
  damaged?: boolean;
  truck?: boolean;
  label?: string;
};
const f = (n: number) => n.toFixed(1);
const poly = (pts: [number, number][]) =>
  "M" + pts.map((p) => f(p[0]) + " " + f(p[1])).join(" L");

function geometry(damaged: boolean) {
  const cableY = (x: number) => 470 - 300 * ((x - 720) / 300) ** 2;
  const main: [number, number][] = [];
  for (let x = 420; x <= 1020; x += 10) main.push([x, cableY(x)]);
  const side = (t: number): [number, number] => [
    (1 - t) ** 2 * 420 + 2 * t * (1 - t) * 180 + t * t * -20,
    (1 - t) ** 2 * 170 + 2 * t * (1 - t) * 330 + t * t * 500,
  ];
  const left: [number, number][] = [];
  const hang: string[] = [];
  for (let t = 0; t <= 1.0001; t += 0.04) left.push(side(t));
  for (let t = 0.1; t <= 0.96; t += 0.07) {
    const p = side(t);
    hang.push(
      `M${f(p[0])} ${f(p[1])} V538`,
      `M${f(1440 - p[0])} ${f(p[1])} V538`,
    );
  }
  for (let x = 450; x <= 990; x += 18) hang.push(`M${x} ${f(cableY(x))} V538`);
  const cables = [
    poly(main),
    poly(left),
    poly(left.map(([x, y]) => [1440 - x, y])),
  ].join(" ");
  const cx = damaged ? 620 : 760;
  const wl = damaged ? 300 : 230;
  const ribY = (x: number, k: number) =>
    526 -
    (12 + 8 * k) *
      Math.exp(-(((x - cx) / 170) ** 2)) *
      Math.sin(((x - 300) / wl) * 2 * Math.PI + k * 0.55) +
    k * 2.2;
  const rib = (k: number) => {
    const pts: [number, number][] = [];
    for (let x = 300; x <= 1140; x += 6) pts.push([x, ribY(x, k)]);
    return poly(pts);
  };
  const top: [number, number][] = [];
  const bottom: [number, number][] = [];
  for (let x = 300; x <= 1140; x += 6) {
    top.push([x, ribY(x, 0)]);
    bottom.push([x, ribY(x, 5)]);
  }
  const band =
    poly(top) +
    " L" +
    bottom
      .reverse()
      .map((p) => f(p[0]) + " " + f(p[1]))
      .join(" L") +
    " Z";
  let seed = 7;
  const rnd = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
  let skyline = "";
  for (let x = 0; x < 1440; x += 18) {
    const w = 12 + rnd() * 14;
    const h = (14 + rnd() * 60) * (x > 380 && x < 1060 ? 0.25 : 1);
    skyline += `M${f(x)} 546 V${f(546 - h)} H${f(x + w)} V546 Z `;
  }
  let stars = "";
  for (let i = 0; i < 70; i++)
    stars += `M${f(rnd() * 1440)} ${f(rnd() * 300)} h0.1 `;
  let shimmer = "";
  for (let i = 0; i < 26; i++) {
    const x = 60 + rnd() * 1320;
    shimmer += `M${f(x)} ${f(570 + rnd() * 20)} V${f(620 + rnd() * 90)} `;
  }
  return {
    hangers: hang.join(" "),
    cables,
    ribs: [0, 1, 2, 3, 4, 5].map(rib),
    band,
    skyline,
    stars,
    shimmer,
  };
}

const DUSK = {
  sky: ["#0A0F2E", "#3B2A73", "#B45B83", "#FF9A66", "#FFD08A"],
  water: "#6A3F7E",
  glow: "#FF9A5C",
  city: "#1A1538",
  stars: 0.25,
};
const NIGHT = {
  sky: ["#050814", "#0C1838", "#17305F", "#2A4F8C", "#4A74B0"],
  water: "#16305F",
  glow: "#3A74FF",
  city: "#0A1230",
  stars: 0.8,
};
const HEALTHY_RIBBON = ["#3DE0D0", "#4C8DFF", "#B98CFF", "#FF8FA3", "#FFB86B"];
const CHANGED_RIBBON = ["#FFB454", "#FF8F6B", "#FF6B6B", "#FF5C8A", "#B98CFF"];

export function BridgeScene({
  mood = "dusk",
  ribbon = true,
  damaged = false,
  truck = false,
  label,
}: Props) {
  const uid = useId().replace(/:/g, "");
  const id = (k: string) => `${k}-${uid}`;
  const url = (k: string) => `url(#${id(k)})`;
  const g = useMemo(() => geometry(damaged), [damaged]);
  const c = mood === "night" ? NIGHT : DUSK;
  const rc = damaged ? CHANGED_RIBBON : HEALTHY_RIBBON;
  const offsets = [0, 0.4, 0.7, 0.9, 1];
  const ribbonStops = [0, 0.3, 0.55, 0.8, 1];
  return (
    <svg
      className="bridge-scene"
      viewBox="0 0 1440 800"
      preserveAspectRatio="xMidYMid slice"
      {...(label
        ? { role: "img", "aria-label": label }
        : { "aria-hidden": true })}
    >
      <defs>
        <linearGradient id={id("sky")} x1="0" y1="0" x2="0" y2="1">
          {c.sky.map((color, i) => (
            <stop key={i} offset={offsets[i]} stopColor={color} />
          ))}
        </linearGradient>
        <linearGradient id={id("water")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={c.water} />
          <stop offset="1" stopColor="#070B14" />
        </linearGradient>
        <radialGradient id={id("glow")} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor={c.glow} stopOpacity="0.75" />
          <stop offset="1" stopColor={c.glow} stopOpacity="0" />
        </radialGradient>
        <linearGradient
          id={id("rib")}
          gradientUnits="userSpaceOnUse"
          x1="300"
          y1="0"
          x2="1140"
          y2="0"
        >
          {rc.map((color, i) => (
            <stop key={i} offset={ribbonStops[i]} stopColor={color} />
          ))}
        </linearGradient>
        <linearGradient id={id("fade")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#070B14" stopOpacity="0" />
          <stop offset="1" stopColor="#070B14" stopOpacity="1" />
        </linearGradient>
        <filter id={id("blur")} x="-0.2" y="-0.6" width="1.4" height="2.2">
          <feGaussianBlur stdDeviation="7" />
        </filter>
        <clipPath id={id("clip")}>
          <rect x="0" y="545" width="1440" height="255" />
        </clipPath>
      </defs>
      <rect width="1440" height="560" fill={url("sky")} />
      <circle cx="1020" cy="548" r="420" fill={url("glow")} />
      <path
        d={g.stars}
        fill="none"
        stroke="#FFFFFF"
        strokeWidth="2.2"
        strokeLinecap="round"
        opacity={c.stars}
      />
      <ellipse
        cx="300"
        cy="300"
        rx="260"
        ry="16"
        fill="#FFB5A0"
        opacity="0.16"
        filter={url("blur")}
      />
      <ellipse
        cx="1180"
        cy="250"
        rx="300"
        ry="18"
        fill="#FFB5A0"
        opacity="0.14"
        filter={url("blur")}
      />
      <ellipse
        cx="760"
        cy="400"
        rx="340"
        ry="12"
        fill="#FFC9A0"
        opacity="0.14"
        filter={url("blur")}
      />
      <path d={g.skyline} fill={c.city} />
      <rect y="545" width="1440" height="255" fill={url("water")} />
      <g id={id("bridge")}>
        <path
          d={g.hangers}
          stroke="#C9B8F5"
          strokeWidth="1"
          opacity="0.55"
          fill="none"
        />
        <path
          d={g.cables}
          stroke="#E5D9FF"
          strokeWidth="2.4"
          fill="none"
          opacity="0.9"
        />
        <path
          d={g.cables}
          stroke="#FFD27A"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray="0.1 11"
          fill="none"
        />
        <g fill="#0C1030" stroke="#8F78C8" strokeWidth="1" strokeOpacity="0.6">
          {[396, 424, 996, 1024].map((x) => (
            <rect key={x} x={x} y="170" width="20" height="392" />
          ))}
          {[390, 990].flatMap((x) =>
            [236, 340, 440].map((y) => (
              <rect key={`${x}-${y}`} x={x} y={y} width="60" height="14" />
            )),
          )}
          <rect x="392" y="160" width="56" height="14" />
          <rect x="992" y="160" width="56" height="14" />
        </g>
        <path
          d="M406 180 V560 M434 180 V560 M1006 180 V560 M1034 180 V560"
          stroke="#FFD27A"
          strokeWidth="2.5"
          strokeDasharray="0.1 14"
          strokeLinecap="round"
          opacity="0.75"
        />
        <rect x="-20" y="538" width="1480" height="9" fill="#0C1030" />
        <line
          x1="-20"
          y1="538"
          x2="1460"
          y2="538"
          stroke="#FFD9A0"
          strokeWidth="2"
          strokeDasharray="0.1 9"
          strokeLinecap="round"
        />
        <line
          x1="-20"
          y1="552"
          x2="1460"
          y2="552"
          stroke="#8F78C8"
          strokeWidth="1"
          opacity="0.5"
        />
      </g>
      {truck && (
        <g transform="translate(120 0)">
          <rect
            x="640"
            y="494"
            width="92"
            height="42"
            rx="2"
            fill="#161C3C"
            stroke="#5A67A8"
            strokeWidth="1.2"
          />
          <rect
            x="734"
            y="506"
            width="28"
            height="30"
            rx="3"
            fill="#1C2347"
            stroke="#5A67A8"
            strokeWidth="1.2"
          />
          <rect
            x="750"
            y="510"
            width="9"
            height="9"
            fill="#FFD9A0"
            opacity="0.8"
          />
          {[660, 716, 750].map((x) => (
            <circle
              key={x}
              cx={x}
              cy="538"
              r="6"
              fill="#0A0F20"
              stroke="#5A67A8"
            />
          ))}
        </g>
      )}
      <g clipPath={url("clip")} opacity="0.28">
        <use
          href={"#" + id("bridge")}
          transform="translate(0 1090) scale(1 -1)"
        />
      </g>
      <path
        d={g.shimmer}
        stroke="#FFB070"
        strokeWidth="2"
        strokeDasharray="1 7"
        strokeLinecap="round"
        opacity="0.4"
        fill="none"
      />
      {ribbon && (
        <g>
          <path d={g.band} fill={url("rib")} opacity="0.22" />
          <path
            d={g.ribs[0]}
            fill="none"
            stroke={url("rib")}
            strokeWidth="12"
            opacity="0.4"
            filter={url("blur")}
          />
          {g.ribs.map((d, k) => (
            <path
              key={k}
              d={d}
              fill="none"
              stroke={url("rib")}
              strokeWidth={2.4 - k * 0.24}
              opacity={1 - k * 0.1}
            />
          ))}
        </g>
      )}
      <rect y="650" width="1440" height="150" fill={url("fade")} />
    </svg>
  );
}
