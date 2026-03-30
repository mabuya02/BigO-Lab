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
    <section className="rounded-xl border border-white/10 bg-[#262626] p-5 shadow-sm w-full mx-auto">
      <header className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-300">{title}</h3>
          <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
        </div>
      </header>
      <div className="w-full min-w-0 relative">
        <ResponsiveContainer width="99%" height={280}>
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id={`fill-${title}`} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.4} />
                <stop offset="100%" stopColor={color} stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey="input_size"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#6b7280", fontSize: 11 }}
              tickMargin={10}
            />
            <YAxis 
              tickLine={false} 
              axisLine={false} 
              tick={{ fill: "#6b7280", fontSize: 11 }} 
              tickMargin={10}
            />
            <Tooltip
              cursor={{ stroke: color, strokeDasharray: "4 4" }}
              contentStyle={{
                backgroundColor: "#1e1e1e",
                borderRadius: "8px",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#d1d5db",
                boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
              }}
              itemStyle={{ color: color, fontWeight: 500 }}
              labelStyle={{ color: "#9ca3af", marginBottom: "4px" }}
            />
            <Area 
              type="monotone" 
              dataKey="value" 
              stroke={color} 
              fill={`url(#fill-${title})`} 
              strokeWidth={2}
              isAnimationActive={true}
              animationDuration={800}
              dot={{ r: 2, fill: color, fillOpacity: 0.8, strokeWidth: 0 }}
              activeDot={{ r: 5, fill: color, stroke: "#262626", strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
