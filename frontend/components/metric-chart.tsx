"use client";

import { ResponsiveContainer, Tooltip, XAxis, YAxis, AreaChart, Area, CartesianGrid } from "recharts";

import type { MetricPoint } from "@/lib/types";

interface MetricChartProps {
  title: string;
  subtitle: string;
  data: MetricPoint[];
  color: string;
}

export function MetricChart({ title, subtitle, data, color }: MetricChartProps) {
  return (
    <section className="rounded-[28px] border border-black/8 bg-white/80 p-5 shadow-[0_20px_50px_rgba(28,26,20,0.08)] backdrop-blur-sm">
      <header className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-[#8c5934]">{title}</h3>
          <p className="mt-1 text-sm text-[#4f5047]">{subtitle}</p>
        </div>
      </header>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id={`fill-${title}`} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.45} />
                <stop offset="100%" stopColor={color} stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(55,53,47,0.1)" vertical={false} />
            <XAxis
              dataKey="input_size"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#4f5047", fontSize: 12 }}
            />
            <YAxis tickLine={false} axisLine={false} tick={{ fill: "#4f5047", fontSize: 12 }} />
            <Tooltip
              cursor={{ stroke: color, strokeDasharray: "5 5" }}
              contentStyle={{
                borderRadius: 16,
                border: "1px solid rgba(55,53,47,0.1)",
                boxShadow: "0 18px 40px rgba(17, 24, 39, 0.12)",
              }}
            />
            <Area type="monotone" dataKey="value" stroke={color} fill={`url(#fill-${title})`} strokeWidth={3} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
