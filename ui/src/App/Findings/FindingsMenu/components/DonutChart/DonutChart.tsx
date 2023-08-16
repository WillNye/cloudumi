import { ResponsivePie } from '@nivo/pie';
import { donutMockData } from './constants';
import styles from './DonutChart.module.css';
import { Icon } from 'shared/elements/Icon';
import { wrapText } from './utils';
import { useMemo } from 'react';

const CenteredMetric = ({
  centerX,
  centerY,
  innerRadius,
  dataWithArc,
  radius
}) => {
  const textContent = 'Are Unused Cloud Identities';

  const percentageValue = useMemo(() => {
    let value = '';
    dataWithArc.forEach(datum => {
      if (datum.id === 'unused') {
        value = `${datum.value}%`;
      }
    });
    return value;
  }, [dataWithArc]);

  const maxWidth = innerRadius * 2;

  // Calculate the available space for the text
  const availableHeight = radius - innerRadius;

  // Split the text into multiple lines
  const lines = wrapText(textContent, maxWidth, availableHeight);

  const lineHeight = useMemo(() => {
    const fontSize = Math.min(availableHeight / lines.length, 12);
    return lines.length * fontSize;
  }, [lines]);

  // Calculate the font size based on the available space

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
        dy="-1em"
        style={{
          fontSize: '24px'
        }}
      >
        {percentageValue}
      </tspan>
      <tspan
        x={centerX}
        dy="5rem"
        style={{
          fontSize: '12px',
          fill: '#999'
        }}
      >
        {lines.map((line, index) => (
          <tspan key={index} x={centerX} dy={index === 0 ? 36 : lineHeight}>
            {line}
          </tspan>
        ))}
      </tspan>
    </text>
  );
};

const customColors = ['#EA3710', '#16B7CD', '#C27565'];

const DonutChart = () => {
  return (
    <div className={styles.donutChart}>
      <h4 className={styles.title}>
        Cloud Indentities
        <Icon name="info" size="medium" />
      </h4>
      <div className={styles.wrapper}>
        <ResponsivePie
          data={donutMockData}
          margin={{ top: 20, bottom: 60 }}
          colors={customColors}
          innerRadius={0.8}
          enableArcLabels={false}
          enableArcLinkLabels={false}
          activeOuterRadiusOffset={5}
          borderWidth={1}
          borderColor={{
            from: 'color',
            modifiers: [['darker', 0.2]]
          }}
          layers={[
            'arcs',
            'arcLabels',
            'arcLinkLabels',
            'legends',
            CenteredMetric
          ]}
          defs={[
            {
              id: 'dots',
              type: 'patternDots',
              background: 'inherit',
              size: 4,
              padding: 1,
              stagger: true
            },
            {
              id: 'lines',
              type: 'patternLines',
              background: 'inherit',
              rotation: -45,
              lineWidth: 6,
              spacing: 10
            }
          ]}
          legends={[
            {
              anchor: 'bottom',
              direction: 'row',
              justify: false,
              translateX: 0,
              translateY: 56,
              itemsSpacing: 0,
              itemWidth: 70,
              itemHeight: 18,
              itemTextColor: '#999',
              itemDirection: 'left-to-right',
              itemOpacity: 1,
              symbolSize: 10,
              symbolShape: 'square'
            }
          ]}
          theme={{
            tooltip: {
              container: {
                background: '#333'
              }
            }
          }}
        />
      </div>
    </div>
  );
};

export default DonutChart;
