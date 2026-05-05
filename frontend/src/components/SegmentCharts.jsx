import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";

const COLORS = [
  "#4f8ef7", "#22c55e", "#f59e0b", "#8b5cf6",
  "#ef4444", "#06b6d4", "#f97316", "#84cc16",
];

const TT_STYLE = {
  backgroundColor: "#181b28",
  border: "1px solid #242736",
  borderRadius: "8px",
  fontSize: 12,
  color: "#ffffff",
  fontWeight: 700,
};

function DonutChart({ data, title }) {
  if (!data?.length) return null;
  const latest = data[0];
  if (!latest?.segments?.length) return null;

  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        {title} — {latest.date}
      </h4>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={latest.segments}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={2}
            label={({ percent }) => `${(percent * 100).toFixed(2)}%`}
            labelLine={false}
          >
            {latest.segments.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v, name) => [`$${Number(v).toFixed(2)}B`, name]}
            contentStyle={TT_STYLE}
            labelStyle={{ color: "#fff", fontWeight: 700 }}
            itemStyle={{ color: "#fff", fontWeight: 700 }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: "#fff", fontWeight: 700 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function StackedChart({ data, title }) {
  if (!data?.length) return null;

  const allNames = [...new Set(data.flatMap((d) => d.segments.map((s) => s.name)))];
  const chartData = [...data].reverse().map((d) => {
    const row = { date: d.date };
    d.segments.forEach((s) => { row[s.name] = s.value; });
    return row;
  });

  return (
    <div className="card p-4">
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        {title} — Historical ($B)
      </h4>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#242736" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={(v) => String(v).slice(0, 4)}
            tick={{ fill: "#fff", fontSize: 11, fontWeight: 700 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#fff", fontSize: 11, fontWeight: 700 }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            formatter={(v, name) => [`$${Number(v).toFixed(2)}B`, name]}
            labelFormatter={(label) => String(label).slice(0, 4)}
            contentStyle={TT_STYLE}
            labelStyle={{ color: "#fff", fontWeight: 700 }}
            itemStyle={{ color: "#fff", fontWeight: 700 }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: "#fff", fontWeight: 700 }} />
          {allNames.map((name, i) => (
            <Bar key={name} dataKey={name} stackId="a" fill={COLORS[i % COLORS.length]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ProductSegmentCharts({ data, isLoading }) {
  if (isLoading || !data?.product?.length) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Business Segments</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DonutChart data={data.product} title="Revenue Mix" />
        <StackedChart data={data.product} title="Revenue Mix" />
      </div>
    </div>
  );
}

export function GeoSegmentCharts({ data, isLoading }) {
  if (isLoading) return null;
  if (!data?.geographic?.length) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Geographic Revenue</h3>
        <p className="text-xs text-muted">Geographic segment data not available for this ticker.</p>
      </div>
    );
  }
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Geographic Revenue</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DonutChart data={data.geographic} title="Region Mix" />
        <StackedChart data={data.geographic} title="Region Mix" />
      </div>
    </div>
  );
}
