import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine, LabelList, Cell,
} from "recharts";

const TT = {
  contentStyle: {
    backgroundColor: "#222224",
    border: "1px solid #2e2e30",
    borderRadius: "8px",
    fontSize: 13,
    color: "#ffffff",
    fontWeight: 700,
  },
  labelStyle: { color: "#ffffff", fontWeight: 700 },
  itemStyle: { color: "#ffffff", fontWeight: 700 },
};

const AXIS_TICK    = { fill: "#9ca3af", fontSize: 12, fontWeight: 600 };
const AXIS_TICK_SM = { fill: "#9ca3af", fontSize: 10, fontWeight: 600 };
const GRID_COLOR   = "#2e2e30";

function shortYear(d) {
  return d ? String(d).slice(0, 4) : "";
}

function shortQuarter(d) {
  if (!d) return "";
  const s = String(d);
  const month = parseInt(s.slice(5, 7), 10);
  const q = Math.ceil(month / 3);
  return `Q${q}'${s.slice(2, 4)}`;
}

function periodLabel(d, period) {
  return period === "quarter" ? shortQuarter(d) : shortYear(d);
}

function sliceData(data, period, quarterLimit = 20) {
  const limit = period === "quarter" ? quarterLimit : 5;
  return [...(data ?? [])].slice(0, limit).reverse();
}

function adapt(count) {
  const dense = count > 8;
  return {
    height: dense ? 340 : 300,
    margin: { top: 44, right: 12, left: 0, bottom: dense ? 55 : 4 },
    xTick: dense ? AXIS_TICK_SM : AXIS_TICK,
    xAngle: dense ? -45 : 0,
    xAnchor: dense ? "end" : "middle",
    xInterval: dense ? 0 : "preserveStartEnd",
    xHeight: dense ? 65 : 30,
    dense,
    dotR: dense ? 2 : 3,
  };
}

function inB(v) {
  return v != null ? +(v / 1e9).toFixed(2) : null;
}

function fmtB(v) {
  if (v == null) return "";
  return v >= 1 ? `$${v.toFixed(2)}B` : `$${(v * 1000).toFixed(2)}M`;
}

function fmtVal(v) {
  if (v == null) return "";
  return `$${Number(v).toFixed(2)}`;
}

function fmtPct(v) {
  if (v == null) return "";
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
}

// Converts absolute-value chartData to YoY growth % for each numeric key
function toGrowthData(chartData, keys) {
  return chartData.map((d, i) => {
    const result = { year: d.year };
    for (const k of keys) {
      const prev = i > 0 ? chartData[i - 1][k] : null;
      if (prev != null && prev !== 0 && d[k] != null) {
        result[k] = +((d[k] - prev) / Math.abs(prev) * 100).toFixed(1);
      } else {
        result[k] = null;
      }
    }
    return result;
  });
}

function growthFill(v) {
  return v == null ? "#3f3f41" : v >= 0 ? "#22c55e" : "#ef4444";
}

// Bar label for absolute figures: value + YoY growth %
function makeBarLabel(chartData, dataKey, valFormatter) {
  return function BarGrowthLabel({ x, y, width, value, index }) {
    if (value == null || !width || width < 8) return null;

    const prev = index > 0 ? chartData[index - 1]?.[dataKey] : null;
    const growth =
      prev != null && prev !== 0
        ? ((value - prev) / Math.abs(prev)) * 100
        : null;

    const dense = chartData.length > 8;
    const fs = dense ? 9 : 10;
    const cx = x + width / 2;
    const growthColor = growth == null ? "#9ca3af" : growth >= 0 ? "#4ade80" : "#ef4444";
    const growthStr =
      growth != null ? `${growth >= 0 ? "+" : ""}${growth.toFixed(1)}%` : null;

    if (dense) {
      return growthStr ? (
        <text x={cx} y={y - 3} textAnchor="middle" fontSize={fs}
          fill={growthColor} fontWeight={700}>{growthStr}</text>
      ) : null;
    }

    return (
      <g>
        {growthStr && (
          <text x={cx} y={y - 14} textAnchor="middle" fontSize={fs}
            fill={growthColor} fontWeight={700}>{growthStr}</text>
        )}
        <text x={cx} y={y - 3} textAnchor="middle" fontSize={fs}
          fill="#e5e7eb" fontWeight={600}>{valFormatter(value)}</text>
      </g>
    );
  };
}

// Bar label for growth % mode: just shows the % value above bar
function makeGrowthLabel() {
  return function GrowthLabel({ x, y, width, value }) {
    if (value == null || !width || width < 8) return null;
    return (
      <text x={x + width / 2} y={y - 3} textAnchor="middle" fontSize={10}
        fill={value >= 0 ? "#4ade80" : "#ef4444"} fontWeight={700}>
        {fmtPct(value)}
      </text>
    );
  };
}

function EmptyChart({ title }) {
  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <div className="h-[240px] flex items-center justify-center text-muted text-sm">
        No data available
      </div>
    </div>
  );
}

export function RevenueChart({ data, isLoading, period = "annual", quarterLimit = 20, chartView = "figures" }) {
  const title = chartView === "growth" ? "Revenue & Gross Profit (YoY Growth %)" : "Revenue & Gross Profit ($B)";
  if (isLoading) return <EmptyChart title={title} />;

  const base = sliceData(data, period, quarterLimit).map((d) => ({
    year: periodLabel(d.date, period),
    Revenue: inB(d.revenue),
    "Gross Profit": inB(d.gross_profit),
  })).filter((d) => d.year && d.Revenue != null);

  if (!base.length) return <EmptyChart title={title} />;

  const isGrowth = chartView === "growth";
  const chartData = isGrowth ? toGrowthData(base, ["Revenue", "Gross Profit"]) : base;
  const a = adapt(chartData.length);

  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={a.height}>
        <BarChart data={chartData} margin={a.margin} barCategoryGap="20%">
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
          <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
            angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45}
            tickFormatter={isGrowth ? (v) => `${v}%` : undefined} />
          <Tooltip {...TT} formatter={(v) => [isGrowth ? fmtPct(v) : `$${v?.toFixed(2)}B`]} />
          <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af", fontWeight: 600 }} />
          {isGrowth && <ReferenceLine y={0} stroke="#3f3f41" />}
          <Bar dataKey="Revenue" radius={[3, 3, 0, 0]}>
            {isGrowth
              ? chartData.map((d, i) => <Cell key={i} fill={growthFill(d.Revenue)} />)
              : null}
            <LabelList content={isGrowth ? makeGrowthLabel() : makeBarLabel(chartData, "Revenue", fmtB)} />
          </Bar>
          <Bar dataKey="Gross Profit" radius={[3, 3, 0, 0]}>
            {isGrowth
              ? chartData.map((d, i) => <Cell key={i} fill={growthFill(d["Gross Profit"])} />)
              : null}
            {!isGrowth && <LabelList content={makeBarLabel(chartData, "Gross Profit", fmtB)} />}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function EPSChart({ data, isLoading, period = "annual", quarterLimit = 20, chartView = "figures" }) {
  const title = chartView === "growth" ? "EPS (YoY Growth %)" : "EPS — Diluted ($)";
  if (isLoading) return <EmptyChart title={title} />;

  const base = sliceData(data, period, quarterLimit).map((d) => ({
    year: periodLabel(d.date, period),
    EPS: d.eps_diluted ?? d.eps,
  })).filter((d) => d.year && d.EPS != null);

  if (!base.length) return <EmptyChart title={title} />;

  const isGrowth = chartView === "growth";
  const chartData = isGrowth ? toGrowthData(base, ["EPS"]) : base;
  const a = adapt(chartData.length);

  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={a.height}>
        <BarChart data={chartData} margin={a.margin}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
          <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
            angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45}
            tickFormatter={isGrowth ? (v) => `${v}%` : undefined} />
          <Tooltip {...TT} formatter={(v) => [isGrowth ? fmtPct(v) : `$${v?.toFixed(2)}`]} />
          <ReferenceLine y={0} stroke="#3f3f41" />
          <Bar dataKey="EPS" radius={[3, 3, 0, 0]}>
            {isGrowth
              ? chartData.map((d, i) => <Cell key={i} fill={growthFill(d.EPS)} />)
              : null}
            <LabelList content={isGrowth ? makeGrowthLabel() : makeBarLabel(chartData, "EPS", fmtVal)} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function NetIncomeChart({ data, isLoading, period = "annual", quarterLimit = 20, chartView = "figures" }) {
  const title = chartView === "growth" ? "Net Income (YoY Growth %)" : "Net Income ($B)";
  if (isLoading) return <EmptyChart title={title} />;

  const base = sliceData(data, period, quarterLimit).map((d) => ({
    year: periodLabel(d.date, period),
    "Net Income": inB(d.net_income),
  })).filter((d) => d.year && d["Net Income"] != null);

  if (!base.length) return <EmptyChart title={title} />;

  const isGrowth = chartView === "growth";
  const chartData = isGrowth ? toGrowthData(base, ["Net Income"]) : base;
  const a = adapt(chartData.length);

  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={a.height}>
        <BarChart data={chartData} margin={a.margin}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
          <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
            angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45}
            tickFormatter={isGrowth ? (v) => `${v}%` : undefined} />
          <Tooltip {...TT} formatter={(v) => [isGrowth ? fmtPct(v) : `$${v?.toFixed(2)}B`]} />
          <ReferenceLine y={0} stroke="#3f3f41" />
          <Bar dataKey="Net Income" radius={[3, 3, 0, 0]}>
            {isGrowth
              ? chartData.map((d, i) => <Cell key={i} fill={growthFill(d["Net Income"])} />)
              : null}
            <LabelList content={isGrowth ? makeGrowthLabel() : makeBarLabel(chartData, "Net Income", fmtB)} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function FCFChart({ data, isLoading, period = "annual", quarterLimit = 20, chartView = "figures" }) {
  const title = chartView === "growth" ? "Free Cash Flow (YoY Growth %)" : "Free Cash Flow ($B)";
  if (isLoading) return <EmptyChart title={title} />;

  const base = sliceData(data, period, quarterLimit).map((d) => ({
    year: periodLabel(d.date, period),
    "Op. Cash Flow": inB(d.operating_cash_flow),
    "Free Cash Flow": inB(d.fcf),
  })).filter((d) => d.year && d["Op. Cash Flow"] != null);

  if (!base.length) return <EmptyChart title={title} />;

  const isGrowth = chartView === "growth";
  const chartData = isGrowth ? toGrowthData(base, ["Op. Cash Flow", "Free Cash Flow"]) : base;
  const a = adapt(chartData.length);

  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={a.height}>
        <BarChart data={chartData} margin={a.margin} barCategoryGap="20%">
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
          <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
            angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45}
            tickFormatter={isGrowth ? (v) => `${v}%` : undefined} />
          <Tooltip {...TT} formatter={(v) => [isGrowth ? fmtPct(v) : `$${v?.toFixed(2)}B`]} />
          <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af", fontWeight: 600 }} />
          <ReferenceLine y={0} stroke="#3f3f41" />
          <Bar dataKey="Op. Cash Flow" fill={isGrowth ? undefined : "#10b981"} radius={[3, 3, 0, 0]}>
            {isGrowth
              ? chartData.map((d, i) => <Cell key={i} fill={growthFill(d["Op. Cash Flow"])} />)
              : null}
            <LabelList content={isGrowth ? makeGrowthLabel() : makeBarLabel(chartData, "Op. Cash Flow", fmtB)} />
          </Bar>
          <Bar dataKey="Free Cash Flow" fill={isGrowth ? undefined : "#22c55e"} radius={[3, 3, 0, 0]}>
            {isGrowth
              ? chartData.map((d, i) => <Cell key={i} fill={growthFill(d["Free Cash Flow"])} />)
              : null}
            {!isGrowth && <LabelList content={makeBarLabel(chartData, "Free Cash Flow", fmtB)} />}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DebtChart({ data, isLoading, period = "annual", quarterLimit = 20, chartView = "figures" }) {
  const title = chartView === "growth" ? "Debt vs Cash (YoY Growth %)" : "Debt vs Cash ($B)";
  if (isLoading) return <EmptyChart title={title} />;

  const base = sliceData(data, period, quarterLimit).map((d) => ({
    year: periodLabel(d.date, period),
    "Total Debt": inB(d.total_debt),
    Cash: inB(d.cash),
    "Net Debt": inB(d.net_debt),
  })).filter((d) => d.year && d["Total Debt"] != null);

  if (!base.length) return <EmptyChart title={title} />;

  const isGrowth = chartView === "growth";
  const chartData = isGrowth ? toGrowthData(base, ["Total Debt", "Cash", "Net Debt"]) : base;
  const a = adapt(chartData.length);

  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={a.height}>
        {isGrowth ? (
          <BarChart data={chartData} margin={a.margin} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
            <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
              angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45}
              tickFormatter={(v) => `${v}%`} />
            <Tooltip {...TT} formatter={(v) => [fmtPct(v)]} />
            <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af", fontWeight: 600 }} />
            <ReferenceLine y={0} stroke="#3f3f41" />
            <Bar dataKey="Total Debt" radius={[3, 3, 0, 0]}>
              {chartData.map((d, i) => <Cell key={i} fill={growthFill(d["Total Debt"])} />)}
              <LabelList content={makeGrowthLabel()} />
            </Bar>
            <Bar dataKey="Cash" radius={[3, 3, 0, 0]}>
              {chartData.map((d, i) => <Cell key={i} fill={growthFill(d.Cash)} />)}
            </Bar>
            <Bar dataKey="Net Debt" radius={[3, 3, 0, 0]}>
              {chartData.map((d, i) => <Cell key={i} fill={growthFill(d["Net Debt"])} />)}
            </Bar>
          </BarChart>
        ) : (
          <LineChart data={chartData} margin={a.margin}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
            <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
              angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45} />
            <Tooltip {...TT} formatter={(v) => [`$${v?.toFixed(2)}B`]} />
            <Legend wrapperStyle={{ fontSize: 12, color: "#9ca3af", fontWeight: 600 }} />
            <Line type="monotone" dataKey="Total Debt" stroke="#ef4444" strokeWidth={2}
              dot={{ r: a.dotR }} activeDot={{ r: 5 }}>
              {!a.dense && (
                <LabelList dataKey="Total Debt" position="top" formatter={fmtB}
                  style={{ fontSize: 10, fill: "#ef4444", fontWeight: 700 }} />
              )}
            </Line>
            <Line type="monotone" dataKey="Cash" stroke="#22c55e" strokeWidth={2}
              dot={{ r: a.dotR }} activeDot={{ r: 5 }}>
              {!a.dense && (
                <LabelList dataKey="Cash" position="top" formatter={fmtB}
                  style={{ fontSize: 10, fill: "#22c55e", fontWeight: 700 }} />
              )}
            </Line>
            <Line type="monotone" dataKey="Net Debt" stroke="#f59e0b" strokeWidth={1.5}
              strokeDasharray="4 2" dot={{ r: a.dotR }} activeDot={{ r: 5 }}>
              {!a.dense && (
                <LabelList dataKey="Net Debt" position="top" formatter={fmtB}
                  style={{ fontSize: 10, fill: "#f59e0b", fontWeight: 700 }} />
              )}
            </Line>
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
