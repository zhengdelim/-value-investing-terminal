import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine, LabelList,
} from "recharts";

const TT = {
  contentStyle: {
    backgroundColor: "#181b28",
    border: "1px solid #242736",
    borderRadius: "8px",
    fontSize: 13,
    color: "#ffffff",
    fontWeight: 700,
  },
  labelStyle: { color: "#ffffff", fontWeight: 700 },
  itemStyle: { color: "#ffffff", fontWeight: 700 },
};

const LABEL_STYLE = { fontSize: 11, fill: "#ffffff", fontWeight: 700 };
const AXIS_TICK   = { fill: "#ffffff", fontSize: 12, fontWeight: 700 };
const AXIS_TICK_SM = { fill: "#ffffff", fontSize: 10, fontWeight: 600 };

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

// Returns layout settings that adapt to the number of data points
function adapt(count) {
  const dense = count > 8;
  return {
    height: dense ? 320 : 280,
    margin: { top: 24, right: 12, left: 0, bottom: dense ? 55 : 4 },
    xTick: dense ? AXIS_TICK_SM : AXIS_TICK,
    xAngle: dense ? -45 : 0,
    xAnchor: dense ? "end" : "middle",
    xInterval: dense ? 0 : "preserveStartEnd",
    xHeight: dense ? 65 : 30,
    showLabels: !dense,
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

export function RevenueChart({ data, isLoading, period = "annual", quarterLimit = 20 }) {
  const title = "Revenue & Gross Profit ($B)";
  if (isLoading) return <EmptyChart title={title} />;

  const chartData = sliceData(data, period, quarterLimit).map((d) => ({
    year: periodLabel(d.date, period),
    Revenue: inB(d.revenue),
    "Gross Profit": inB(d.gross_profit),
  })).filter((d) => d.year && d.Revenue != null);

  if (!chartData.length) return <EmptyChart title={title} />;

  const a = adapt(chartData.length);
  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={a.height}>
        <BarChart data={chartData} margin={a.margin} barCategoryGap="20%">
          <CartesianGrid strokeDasharray="3 3" stroke="#242736" vertical={false} />
          <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
            angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45} />
          <Tooltip {...TT} formatter={(v) => [`$${v?.toFixed(2)}B`]} />
          <Legend wrapperStyle={{ fontSize: 12, color: "#ffffff", fontWeight: 700 }} />
          <Bar dataKey="Revenue" fill="#4f8ef7" radius={[3, 3, 0, 0]}>
            {a.showLabels && <LabelList dataKey="Revenue" position="top" formatter={fmtB} style={LABEL_STYLE} />}
          </Bar>
          <Bar dataKey="Gross Profit" fill="#22c55e" radius={[3, 3, 0, 0]}>
            {a.showLabels && <LabelList dataKey="Gross Profit" position="top" formatter={fmtB} style={LABEL_STYLE} />}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function EPSChart({ data, isLoading, period = "annual", quarterLimit = 20 }) {
  const title = "EPS — Diluted ($)";
  if (isLoading) return <EmptyChart title={title} />;

  const chartData = sliceData(data, period, quarterLimit).map((d) => ({
    year: periodLabel(d.date, period),
    EPS: d.eps_diluted ?? d.eps,
  })).filter((d) => d.year && d.EPS != null);

  if (!chartData.length) return <EmptyChart title={title} />;

  const a = adapt(chartData.length);
  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={a.height}>
        <BarChart data={chartData} margin={a.margin}>
          <CartesianGrid strokeDasharray="3 3" stroke="#242736" vertical={false} />
          <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
            angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45} />
          <Tooltip {...TT} formatter={(v) => [`$${v?.toFixed(2)}`]} />
          <ReferenceLine y={0} stroke="#374151" />
          <Bar dataKey="EPS" fill="#8b5cf6" radius={[3, 3, 0, 0]}>
            {a.showLabels && (
              <LabelList dataKey="EPS" position="top"
                formatter={(v) => `$${v?.toFixed(2)}`}
                style={LABEL_STYLE} />
            )}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function NetIncomeChart({ data, isLoading, period = "annual", quarterLimit = 20 }) {
  const title = "Net Income ($B)";
  if (isLoading) return <EmptyChart title={title} />;

  const chartData = sliceData(data, period, quarterLimit).map((d) => ({
    year: periodLabel(d.date, period),
    "Net Income": inB(d.net_income),
  })).filter((d) => d.year && d["Net Income"] != null);

  if (!chartData.length) return <EmptyChart title={title} />;

  const a = adapt(chartData.length);
  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={a.height}>
        <BarChart data={chartData} margin={a.margin}>
          <CartesianGrid strokeDasharray="3 3" stroke="#242736" vertical={false} />
          <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
            angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45} />
          <Tooltip {...TT} formatter={(v) => [`$${v?.toFixed(2)}B`]} />
          <ReferenceLine y={0} stroke="#374151" />
          <Bar dataKey="Net Income" fill="#f59e0b" radius={[3, 3, 0, 0]}>
            {a.showLabels && <LabelList dataKey="Net Income" position="top" formatter={fmtB} style={LABEL_STYLE} />}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function FCFChart({ data, isLoading, period = "annual", quarterLimit = 20 }) {
  const title = "Free Cash Flow ($B)";
  if (isLoading) return <EmptyChart title={title} />;

  const chartData = sliceData(data, period, quarterLimit).map((d) => ({
    year: periodLabel(d.date, period),
    "Op. Cash Flow": inB(d.operating_cash_flow),
    "Free Cash Flow": inB(d.fcf),
  })).filter((d) => d.year && d["Free Cash Flow"] != null);

  if (!chartData.length) return <EmptyChart title={title} />;

  const a = adapt(chartData.length);
  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={a.height}>
        <BarChart data={chartData} margin={a.margin} barCategoryGap="20%">
          <CartesianGrid strokeDasharray="3 3" stroke="#242736" vertical={false} />
          <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
            angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45} />
          <Tooltip {...TT} formatter={(v) => [`$${v?.toFixed(2)}B`]} />
          <Legend wrapperStyle={{ fontSize: 12, color: "#ffffff", fontWeight: 700 }} />
          <ReferenceLine y={0} stroke="#374151" />
          <Bar dataKey="Op. Cash Flow" fill="#4f8ef7" radius={[3, 3, 0, 0]}>
            {a.showLabels && <LabelList dataKey="Op. Cash Flow" position="top" formatter={fmtB} style={LABEL_STYLE} />}
          </Bar>
          <Bar dataKey="Free Cash Flow" fill="#22c55e" radius={[3, 3, 0, 0]}>
            {a.showLabels && <LabelList dataKey="Free Cash Flow" position="top" formatter={fmtB} style={LABEL_STYLE} />}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DebtChart({ data, isLoading, period = "annual", quarterLimit = 20 }) {
  const title = "Debt vs Cash ($B)";
  if (isLoading) return <EmptyChart title={title} />;

  const chartData = sliceData(data, period, quarterLimit).map((d) => ({
    year: periodLabel(d.date, period),
    "Total Debt": inB(d.total_debt),
    Cash: inB(d.cash),
    "Net Debt": inB(d.net_debt),
  })).filter((d) => d.year && d["Total Debt"] != null);

  if (!chartData.length) return <EmptyChart title={title} />;

  const a = adapt(chartData.length);
  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h4>
      <ResponsiveContainer width="100%" height={a.height}>
        <LineChart data={chartData} margin={a.margin}>
          <CartesianGrid strokeDasharray="3 3" stroke="#242736" vertical={false} />
          <XAxis dataKey="year" tick={a.xTick} axisLine={false} tickLine={false}
            angle={a.xAngle} textAnchor={a.xAnchor} interval={a.xInterval} height={a.xHeight} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={45} />
          <Tooltip {...TT} formatter={(v) => [`$${v?.toFixed(2)}B`]} />
          <Legend wrapperStyle={{ fontSize: 12, color: "#ffffff", fontWeight: 700 }} />
          <Line type="monotone" dataKey="Total Debt" stroke="#ef4444" strokeWidth={2} dot={{ r: a.dotR }} activeDot={{ r: 5 }}>
            {a.showLabels && <LabelList dataKey="Total Debt" position="top" formatter={fmtB} style={{ ...LABEL_STYLE, fill: "#ef4444" }} />}
          </Line>
          <Line type="monotone" dataKey="Cash" stroke="#22c55e" strokeWidth={2} dot={{ r: a.dotR }} activeDot={{ r: 5 }}>
            {a.showLabels && <LabelList dataKey="Cash" position="top" formatter={fmtB} style={{ ...LABEL_STYLE, fill: "#22c55e" }} />}
          </Line>
          <Line type="monotone" dataKey="Net Debt" stroke="#f59e0b" strokeWidth={1.5} strokeDasharray="4 2" dot={{ r: a.dotR }} activeDot={{ r: 5 }}>
            {a.showLabels && <LabelList dataKey="Net Debt" position="top" formatter={fmtB} style={{ ...LABEL_STYLE, fill: "#f59e0b" }} />}
          </Line>
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
