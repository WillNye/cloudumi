import { useMemo } from 'react';
import { wrapText } from './utils';

export const CustomTooltip = ({ datum }) => {
  return (
    <div
      style={{
        background: '#101114',
        border: '1px solid #696D77',
        padding: '5px',
        display: 'flex',
        alignItems: 'center',
        borderRadius: '5px'
      }}
    >
      <div
        style={{
          backgroundColor: datum.color,
          height: '10px',
          width: '10px',
          marginRight: '5px'
        }}
      ></div>

      <div style={{ fontSize: '11px', fontWeight: 500 }}>
        {datum.label}: {datum.value} | {datum.formattedValue}%
      </div>
    </div>
  );
};

export const CenteredMetric = ({
  centerX,
  centerY,
  innerRadius,
  radius,
  labelTitle = '',
  labelDescription = ''
}) => {
  const maxWidth = innerRadius * 2;

  // Calculate the available space for the text
  const availableHeight = radius - innerRadius;

  // Split the text into multiple lines
  const lines = wrapText(labelTitle, maxWidth, availableHeight);

  const lineHeight = useMemo(() => {
    const fontSize = Math.min(availableHeight / lines.length, 11);
    return lines.length * fontSize;
  }, [availableHeight, lines.length]);

  return (
    <text
      x={centerX}
      y={centerY}
      textAnchor="middle"
      dominantBaseline="central"
      style={{
        fontWeight: 600,
        fill: 'white',
        maxWidth: `${innerRadius}px`
      }}
    >
      <tspan
        x={centerX}
        dy="-0.8em"
        style={{
          fontSize: '24px'
        }}
      >
        {labelDescription}
      </tspan>
      <tspan
        x={centerX}
        dy="5rem"
        style={{
          fontSize: '11px',
          fill: '#878A96'
        }}
      >
        {lines.map((line, index) => (
          <tspan key={index} x={centerX} dy={index === 0 ? 24 : lineHeight}>
            {line}
          </tspan>
        ))}
      </tspan>
    </text>
  );
};
