import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const DataChart = ({ data }) => {
  if (!data || data.length === 0) return null;

  // Attempt to intelligently map the data keys to Chart X/Y axes
  // Usually, a SQL result has 1-3 columns. 
  // We look for a string/name column for X, and a number column for Y.
  
  const keys = Object.keys(data[0]);
  let xKey = keys[0];
  let yKey = keys.length > 1 ? keys[1] : keys[0];

  // Try to find a numeric column for Y, and non-numeric for X
  for (const key of keys) {
      if (typeof data[0][key] === 'number') {
          yKey = key;
      } else if (typeof data[0][key] === 'string') {
          xKey = key;
      }
  }

  // Format Y Axis for financial numbers if it looks large
  const formatYAxis = (tickItem) => {
    if (tickItem >= 1000000) return `$${(tickItem / 1000000).toFixed(1)}M`;
    if (tickItem >= 1000) return `${(tickItem / 1000).toFixed(1)}k`;
    return tickItem;
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
            backgroundColor: '#1E1E2D',
            padding: '10px 15px',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
            color: '#E2E8F0',
            boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
        }}>
          <p style={{ margin: 0, fontWeight: 600, marginBottom: '5px' }}>{label}</p>
          <p style={{ margin: 0, color: '#4ADE80' }}>
            <span style={{color: '#94A3B8', marginRight: '5px'}}>{yKey}:</span> 
            {payload[0].value.toLocaleString()}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: 300, marginTop: '20px', padding: '15px', backgroundColor: 'rgba(20, 20, 30, 0.4)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
      <h4 style={{ margin: '0 0 15px 0', fontSize: '13px', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Data Visualization
      </h4>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <XAxis 
            dataKey={xKey} 
            stroke="#475569" 
            tick={{ fill: '#94A3B8', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis 
            stroke="#475569" 
            tickFormatter={formatYAxis} 
            tick={{ fill: '#94A3B8', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{fill: 'rgba(255,255,255,0.03)'}} />
          <Bar dataKey={yKey} radius={[4, 4, 0, 0]} maxBarSize={50}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#4ADE80' : '#2DD4BF'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DataChart;
