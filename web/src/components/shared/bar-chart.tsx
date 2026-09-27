"use client";

interface BarChartProps {
  data: { label: string; gross: number; fees: number; net: number }[];
  height?: number;
  loading?: boolean;
}

const SERIES = [
  { key: "gross" as const, fill: "hsl(0 0% 16%)", stroke: "hsl(0 0% 16%)", name: "Gross" },
  { key: "fees" as const, fill: "hsl(0 0% 82%)", stroke: "hsl(0 0% 55%)", name: "Platform fees" },
  { key: "net" as const, fill: "hsl(0 0% 48%)", stroke: "hsl(0 0% 48%)", name: "Net" },
];

export function BarChart({ data, height = 220, loading }: BarChartProps) {
  if (loading) {
    return <div className="animate-pulse rounded-md bg-muted" style={{ height }} />;
  }
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-md border border-dashed text-xs text-muted-foreground" style={{ height }}>
        No data for this range yet
      </div>
    );
  }

  const max = Math.max(...data.map((d) => Math.max(d.gross, d.fees, d.net)), 1);
  const groupWidth = 100 / data.length;
  const barWidth = Math.min(groupWidth / 4.2, 6);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-4">
        {SERIES.map((s) => (
          <span key={s.key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span
              className="h-2.5 w-2.5 rounded-sm border"
              style={{ background: s.fill, borderColor: s.stroke }}
            />
            {s.name}
          </span>
        ))}
      </div>
      <svg
        viewBox={`0 0 100 ${34}`}
        preserveAspectRatio="none"
        role="img"
        aria-label="Earnings chart"
        style={{ height, width: "100%" }}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <line key={t} x1="0" x2="100" y1={t * 30} y2={t * 30}
                stroke="hsl(0 0% 90%)" strokeWidth="0.15" vectorEffect="non-scaling-stroke" />
        ))}
        {data.map((d, i) => {
          const cx = groupWidth * i + groupWidth / 2;
          return SERIES.map((s, j) => {
            const value = d[s.key];
            const h = (value / max) * 29;
            const x = cx - (SERIES.length * barWidth + (SERIES.length - 1) * 0.4) / 2 + j * (barWidth + 0.4);
            return (
              <rect key={s.key} x={x} y={30 - h} width={barWidth} height={Math.max(h, value > 0 ? 0.3 : 0)}
                    rx="0.3" fill={s.fill} stroke={s.stroke} strokeWidth="0.12"
                    vectorEffect="non-scaling-stroke">
                <title>{`${d.label} — ${s.name}: $${value.toLocaleString("en-US", { minimumFractionDigits: 2 })}`}</title>
              </rect>
            );
          });
        })}
      </svg>
      <div className="mt-2 flex justify-between text-[10px] text-muted-foreground">
        {data.map((d, i) => (
          <span key={i} className="truncate px-0.5" style={{ width: `${groupWidth}%` }}>{d.label}</span>
        ))}
      </div>
    </div>
  );
}
