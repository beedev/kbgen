import React from 'react';
import {
  Bar,
  BarChart as RCBarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

// Thin wrapper over recharts. Matches the Chart API we used previously but
// only supports bar charts (all kbgen dashboards currently need is a bar or
// a stacked-bar for topic volume).
export function BarChart<T extends Record<string, any>>({
  data,
  xKey,
  yKeys,
  height = 260,
  stacked = false,
}: {
  data: T[];
  xKey: string;
  yKeys: string[];
  height?: number;
  stacked?: boolean;
}) {
  const palette = [
    'var(--kbgen-brand)',
    'var(--kbgen-success)',
    'var(--kbgen-warning)',
    'var(--kbgen-danger)',
    'var(--kbgen-info)',
  ];
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <RCBarChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 10 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="var(--kbgen-border)" vertical={false} />
          <XAxis
            dataKey={xKey}
            interval={0}
            angle={-20}
            dy={10}
            tick={{ fontSize: 11, fill: 'var(--kbgen-text-secondary)' }}
          />
          <YAxis tick={{ fontSize: 11, fill: 'var(--kbgen-text-secondary)' }} />
          <Tooltip
            contentStyle={{
              background: 'var(--kbgen-surface)',
              border: '1px solid var(--kbgen-border)',
              fontSize: 12,
            }}
          />
          {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
          {yKeys.map((k, i) => (
            <Bar
              key={k}
              dataKey={k}
              stackId={stacked ? 'a' : undefined}
              fill={palette[i % palette.length]}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </RCBarChart>
      </ResponsiveContainer>
    </div>
  );
}
