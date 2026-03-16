import React from 'react';

interface DoraTrendChartProps {
  title: string;
  data: number[];
}

function DoraTrendChart({ title, data }: DoraTrendChartProps) {
  const max = Math.max(...data, 1);
  return (
    <div style={{ border: '1px solid #e0e0e0', borderRadius: 8, padding: 16 }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: 14, color: '#666' }}>{title}</h3>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 80 }}>
        {data.map((val, i) => {
          const barKey = `bar-${String(val)}-${String(i)}`;
          return (
            <div
              key={barKey}
              data-testid="trend-bar"
              style={{
                flex: 1,
                height: `${(val / max) * 100}%`,
                backgroundColor: '#1976d2',
                borderRadius: '2px 2px 0 0',
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

export default DoraTrendChart;
