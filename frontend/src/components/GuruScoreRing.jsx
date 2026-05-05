import clsx from "clsx";

function ringColor(score) {
  if (score >= 70) return { stroke: "#22c55e", text: "text-green" };
  if (score >= 45) return { stroke: "#f59e0b", text: "text-yellow" };
  return { stroke: "#ef4444", text: "text-red" };
}

export default function GuruScoreRing({ score, size = 56 }) {
  const r = (size / 2) * 0.78;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(Math.max(score ?? 0, 0), 100) / 100;
  const dash = pct * circ;
  const { stroke, text } = ringColor(score ?? 0);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#242736"
          strokeWidth={size * 0.1}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth={size * 0.1}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
        />
      </svg>
      <span
        className={clsx("absolute font-mono font-semibold", text)}
        style={{ fontSize: size * 0.26 }}
      >
        {score != null ? Math.round(score) : "—"}
      </span>
    </div>
  );
}

export function ScorePillar({ label, value, color }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[10px] text-muted uppercase tracking-widest">{label}</span>
      <span className={clsx("font-mono font-semibold text-sm", color ?? "text-gray-300")}>
        {value != null ? Math.round(value) : "—"}
      </span>
    </div>
  );
}
