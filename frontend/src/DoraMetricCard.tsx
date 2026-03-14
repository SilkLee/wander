import React from 'react';

interface DoraMetricCardProps {
  name: string;
  value: string;
  rating?: string;
}

function DoraMetricCard({ name, value, rating }: DoraMetricCardProps) {
  return (
    <div style={{ border: '1px solid #e0e0e0', borderRadius: 8, padding: 16, minWidth: 200 }}>
      <h3 style={{ margin: 0, fontSize: 14, color: '#666' }}>{name}</h3>
      <p style={{ margin: '8px 0', fontSize: 24, fontWeight: 'bold' }}>{value}</p>
      {rating && <span style={{ fontSize: 12, color: '#4caf50' }}>{rating}</span>}
    </div>
  );
}

export default DoraMetricCard;
