import clsx from "clsx";

export function scoreBand(value, low, high) {
  if (value === null || value === undefined) return "neutral";
  if (value >= high) return "green";
  if (value >= low) return "yellow";
  return "red";
}

const BAND_CLASSES = {
  green: "bg-green-bg text-green border border-green/20",
  yellow: "bg-yellow-bg text-yellow border border-yellow/20",
  red: "bg-red-bg text-red border border-red/20",
  neutral: "bg-bg-hover text-muted border border-bg-border",
};

export default function Badge({ value, label, band, formatter }) {
  const resolvedBand = band ?? "neutral";
  const display = formatter ? formatter(value) : (value ?? "—");

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-mono font-medium",
        BAND_CLASSES[resolvedBand]
      )}
    >
      {label && <span className="font-sans text-[10px] opacity-70">{label}</span>}
      {display}
    </span>
  );
}

export function MetricBadge({ value, label, good, bad, invert = false, pct = false, unit = "" }) {
  const fmt = (v) =>
    v === null || v === undefined
      ? "—"
      : pct
      ? `${(v * 100).toFixed(1)}%`
      : `${v.toFixed(2)}${unit}`;

  let band = "neutral";
  if (value !== null && value !== undefined) {
    const norm = invert ? -value : value;
    const goodN = invert ? -good : good;
    const badN = invert ? -bad : bad;
    band = scoreBand(norm, (goodN + badN) / 2, goodN);
  }

  return <Badge value={value} label={label} band={band} formatter={fmt} />;
}
