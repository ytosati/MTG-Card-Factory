// Concept D "Forge" (tasks.md T251): original drawn ornaments: the gear mark, runes, filigree, card back, gauge.
import { useId } from "react";

import type { PowerIndicator } from "../../../../api/types";

const point = (cx: number, cy: number, r: number, angle: number): string =>
  `${(cx + r * Math.cos(angle)).toFixed(2)},${(cy + r * Math.sin(angle)).toFixed(2)}`;

/** The outline of a gear with square teeth, as an SVG path. */
export function gearPath(cx: number, cy: number, outer: number, inner: number, teeth: number): string {
  const step = (Math.PI * 2) / teeth;
  const points: string[] = [];
  for (let index = 0; index < teeth; index += 1) {
    const a = index * step - Math.PI / 2;
    points.push(point(cx, cy, inner, a), point(cx, cy, outer, a + step * 0.16));
    points.push(point(cx, cy, outer, a + step * 0.48), point(cx, cy, inner, a + step * 0.64));
  }
  return `M${points.join("L")}Z`;
}

/** The Card Factory mark: a gold gear around a violet hearth. */
export function GearMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <path d={gearPath(16, 16, 15, 12, 10)} fill="#e8b33a" />
      <circle cx="16" cy="16" r="8.4" fill="#110d18" />
      <circle cx="16" cy="16" r="6.6" fill="none" stroke="#e8b33a" strokeWidth="1.2" />
      <path d="M16 11.2 L19.6 16 L16 20.8 L12.4 16 Z" fill="#a46bff" />
    </svg>
  );
}

/** Original rune strokes in a 6 by 10 box; not taken from any script. */
export const RUNES: readonly string[] = [
  "M1 0V10M1 3L5 0M1 6L5 3",
  "M3 0V10M0 3L3 5L6 3",
  "M1 0V10M5 0V10M1 4L5 7",
  "M0 0L3 5L0 10M6 0L3 5L6 10",
  "M3 0V10M3 0L6 3L3 6",
  "M0 2L3 0L6 2M3 0V10M1 10H5",
  "M1 10V0L5 4L1 8",
  "M0 5L3 0L6 5L3 10Z",
  "M3 0V10M0 4L6 7",
  "M1 0V10M1 0L5 2V5L1 7",
  "M0 0L6 10M6 0L3 5",
  "M3 10V3M0 0L3 3L6 0",
];

/** A row of runes from a seed; each rune is one path so it can be drawn stroke by stroke. */
export function RuneLine(props: { seed: number; count: number; className?: string; runeClass?: string; state?: string }) {
  const { seed, count, className, runeClass, state } = props;
  const width = count * 9;
  return (
    <svg className={className} data-state={state} viewBox={`-1 -1 ${width + 1} 12`} preserveAspectRatio="xMinYMid meet" aria-hidden="true" focusable="false">
      {Array.from({ length: count }, (_, index) => (
        <path
          key={index}
          className={runeClass}
          d={RUNES[(seed * 7 + index * 5) % RUNES.length]}
          transform={`translate(${index * 9} 0)`}
          pathLength={1}
          style={{ animationDelay: `${index * 90}ms` }}
        />
      ))}
    </svg>
  );
}

/** A ring of runes around a centre, for the strong reveal. */
export function RuneRing({ className }: { className?: string }) {
  const count = 18;
  return (
    <svg className={className} viewBox="0 0 200 200" aria-hidden="true" focusable="false">
      <circle cx="100" cy="100" r="96" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.6" />
      <circle cx="100" cy="100" r="76" fill="none" stroke="currentColor" strokeWidth="0.6" opacity="0.45" />
      {Array.from({ length: count }, (_, index) => {
        const angle = (index * 360) / count;
        return (
          <path
            key={index}
            d={RUNES[(index * 5) % RUNES.length]}
            transform={`rotate(${angle} 100 100) translate(97 8)`}
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        );
      })}
    </svg>
  );
}

/** One corner curl of the filigree, drawn for the top-left corner of a 630 by 880 card. */
const CURL_SCROLLS =
  "M30 150 C30 80 80 30 150 30 M44 118 C44 74 74 44 118 44 M44 118 C44 100 56 92 66 96 C76 100 74 114 64 114 " +
  "M118 44 C100 44 92 56 96 66 C100 76 114 74 114 64";
const CURL = `${CURL_SCROLLS} M30 190 V150 M190 30 H150`;

function Corners({ stroke, width, path = CURL }: { stroke: string; width: number; path?: string }) {
  return (
    <g fill="none" stroke={stroke} strokeWidth={width} strokeLinecap="round">
      <path d={path} />
      <path d={path} transform="translate(630 0) scale(-1 1)" />
      <path d={path} transform="translate(0 880) scale(1 -1)" />
      <path d={path} transform="translate(630 880) scale(-1 -1)" />
    </g>
  );
}

/** The gold filigree laid over a card face: corner curls and a fine inner line. */
export function Filigree({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 630 880" preserveAspectRatio="none" aria-hidden="true" focusable="false">
      <rect x="18" y="18" width="594" height="844" rx="20" fill="none" stroke="#e8b33a" strokeOpacity="0.5" strokeWidth="1.5" />
      <g transform="translate(-6 -6) scale(1.02)">
        <Corners stroke="#f0c75e" width={2.2} path={CURL_SCROLLS} />
      </g>
      <circle cx="315" cy="18" r="5" fill="#e8b33a" />
      <circle cx="315" cy="862" r="5" fill="#e8b33a" />
    </svg>
  );
}

const ANVIL =
  "M226 412 H362 V428 C348 432 338 436 330 442 V458 L348 472 V482 H282 V472 L300 458 V442 " +
  "C288 436 276 432 262 430 C248 428 236 422 226 412 Z";

/** The original back of a Card Factory card: violet lacquer, gold filigree, a gear around an anvil. */
export function CardBack({ className }: { className?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg className={className} viewBox="0 0 630 880" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}-gold`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#f8dc8e" />
          <stop offset="0.3" stopColor="#c48f25" />
          <stop offset="0.5" stopColor="#f3cf6a" />
          <stop offset="0.75" stopColor="#8a5e14" />
          <stop offset="1" stopColor="#e8b33a" />
        </linearGradient>
        <radialGradient id={`${id}-lacquer`} cx="0.5" cy="0.46" r="0.7">
          <stop offset="0" stopColor="#4a2290" />
          <stop offset="0.45" stopColor="#2a1350" />
          <stop offset="1" stopColor="#130a22" />
        </radialGradient>
        <pattern id={`${id}-lattice`} width="42" height="42" patternUnits="userSpaceOnUse">
          <path d="M21 0 L42 21 L21 42 L0 21 Z" fill="none" stroke="#e8b33a" strokeOpacity="0.13" strokeWidth="1" />
          <circle cx="21" cy="21" r="1.6" fill="#e8b33a" fillOpacity="0.22" />
        </pattern>
      </defs>
      <rect width="630" height="880" rx="34" fill={`url(#${id}-gold)`} />
      <rect x="13" y="13" width="604" height="854" rx="24" fill={`url(#${id}-lacquer)`} />
      <rect x="13" y="13" width="604" height="854" rx="24" fill={`url(#${id}-lattice)`} />
      <rect x="34" y="34" width="562" height="812" rx="16" fill="none" stroke={`url(#${id}-gold)`} strokeWidth="3" />
      <rect x="46" y="46" width="538" height="788" rx="11" fill="none" stroke="#e8b33a" strokeOpacity="0.55" strokeWidth="1" />
      <g transform="translate(16 16) scale(0.95)">
        <Corners stroke="#f0c75e" width={3} />
      </g>
      <path d="M315 96 L330 116 L315 136 L300 116 Z" fill="#a46bff" stroke="#f0c75e" strokeWidth="2" />
      <path d="M315 744 L330 764 L315 784 L300 764 Z" fill="#a46bff" stroke="#f0c75e" strokeWidth="2" />
      <path d="M170 116 H285 M345 116 H460 M170 764 H285 M345 764 H460" stroke="#e8b33a" strokeOpacity="0.7" strokeWidth="1.5" />

      <circle cx="315" cy="440" r="176" fill="none" stroke="#e8b33a" strokeOpacity="0.45" strokeWidth="1.2" />
      <circle cx="315" cy="440" r="160" fill="none" stroke={`url(#${id}-gold)`} strokeWidth="2.5" />
      <path d={gearPath(315, 440, 140, 120, 18)} fill={`url(#${id}-gold)`} />
      <circle cx="315" cy="440" r="104" fill="#1a0d31" />
      <circle cx="315" cy="440" r="96" fill="none" stroke="#e8b33a" strokeOpacity="0.6" strokeWidth="1.5" />
      <path d={ANVIL} transform="translate(-6 -12)" fill={`url(#${id}-gold)`} />
      <path d="M315 360 V384 M282 372 L294 390 M348 372 L336 390" stroke="#c99bff" strokeWidth="5" strokeLinecap="round" />
      <path d="M315 486 L326 500 L315 514 L304 500 Z" fill="#a46bff" />
      <text
        x="315"
        y="690"
        textAnchor="middle"
        fill="#f0c75e"
        fontFamily="'Bodoni 72', Didot, 'Bodoni MT', Constantia, Georgia, serif"
        fontSize="34"
        fontWeight="600"
        letterSpacing="9"
      >
        CARD FACTORY
      </text>
    </svg>
  );
}

const NEEDLE_ANGLE: Record<PowerIndicator, number> = { too_weak: -58, in_range: 0, too_strong: 58 };

/** An engraved dial for the power indicator: three bands and a needle on the assessed one. */
export function PowerGauge({ indicator, className }: { indicator: PowerIndicator; className?: string }) {
  const arc = (from: number, to: number): string => {
    const r = 80;
    const a = ((from - 90) * Math.PI) / 180;
    const b = ((to - 90) * Math.PI) / 180;
    return `M${point(100, 100, r, a)} A${r} ${r} 0 0 1 ${point(100, 100, r, b)}`;
  };
  const bands: [PowerIndicator, number, number][] = [
    ["too_weak", -88, -31],
    ["in_range", -29, 29],
    ["too_strong", 31, 88],
  ];
  return (
    <svg className={className} viewBox="0 0 200 112" aria-hidden="true" focusable="false">
      {bands.map(([band, from, to]) => (
        <path
          key={band}
          d={arc(from, to)}
          fill="none"
          stroke={band === indicator ? "#e8b33a" : "#4a3a5c"}
          strokeWidth="12"
        />
      ))}
      {Array.from({ length: 19 }, (_, index) => {
        const angle = ((-90 + index * 10 - 90) * Math.PI) / 180;
        const long = index % 3 === 0;
        return (
          <path
            key={index}
            d={`M${point(100, 100, 66, angle)} L${point(100, 100, long ? 56 : 61, angle)}`}
            stroke="#a8761c"
            strokeWidth={long ? 1.6 : 1}
          />
        );
      })}
      <g transform={`rotate(${NEEDLE_ANGLE[indicator]} 100 100)`}>
        <path d="M100 26 L104 100 L96 100 Z" fill="#f3e9ff" />
      </g>
      <circle cx="100" cy="100" r="9" fill="#e8b33a" />
      <circle cx="100" cy="100" r="3.5" fill="#6d28d9" />
    </svg>
  );
}

/** A small round pressure gauge for the machinery around the stage. */
export function SmallGauge({ className, value = 0.62 }: { className?: string; value?: number }) {
  const angle = -120 + value * 240;
  return (
    <svg className={className} viewBox="0 0 40 40" aria-hidden="true" focusable="false">
      <circle cx="20" cy="20" r="19" fill="#a8761c" />
      <circle cx="20" cy="20" r="16.5" fill="#f1e6cf" />
      {Array.from({ length: 9 }, (_, index) => {
        const a = ((-120 + index * 30 - 90) * Math.PI) / 180;
        return <path key={index} d={`M${point(20, 20, 14, a)} L${point(20, 20, 11.5, a)}`} stroke="#3a2a14" strokeWidth="1" />;
      })}
      <g transform={`rotate(${angle} 20 20)`}>
        <path d="M20 7 L21.4 20 L18.6 20 Z" fill="#b62a17" />
      </g>
      <circle cx="20" cy="20" r="2.4" fill="#3a2a14" />
    </svg>
  );
}
