import { ResponsivePie } from '@nivo/pie';
import { donutMockData } from './constants';

const CenteredMetric = ({ centerX, centerY }) => {
  // let total = 0
  // dataWithArc.forEach(datum => {
  //     total += datum.value
  // })

  return (
    <text
      x={centerX}
      y={centerY}
      textAnchor="middle"
      dominantBaseline="central"
      style={{
        // fontSize: '52px',
        fontWeight: 600
        // color: 'white',
        // backgroundColor: "white"
      }}
    >
      Test Data
    </text>
  );
};

const DonutChart = () => {
  return (
    <div style={{ height: 350 }}>
      <ResponsivePie
        data={donutMockData}
        margin={{ top: 40, right: 80, bottom: 80, left: 80 }}
        // innerRadius={0.5}
        padAngle={0.7}
        cornerRadius={3}
        innerRadius={0.8}
        enableArcLabels={false}
        activeOuterRadiusOffset={8}
        borderWidth={1}
        // arcLinkLabel="Test Link Data"
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
        arcLinkLabelsSkipAngle={10}
        arcLinkLabelsTextColor="#333333"
        arcLinkLabelsThickness={2}
        arcLinkLabelsColor={{ from: 'color' }}
        arcLabelsSkipAngle={10}
        arcLabelsTextColor={{
          from: 'color',
          modifiers: [['darker', 2]]
        }}
        defs={[
          {
            id: 'dots',
            type: 'patternDots',
            background: 'inherit',
            color: 'rgba(255, 255, 255, 0.3)',
            size: 4,
            padding: 1,
            stagger: true
          },
          {
            id: 'lines',
            type: 'patternLines',
            background: 'inherit',
            color: 'rgba(255, 255, 255, 0.3)',
            rotation: -45,
            lineWidth: 6,
            spacing: 10
          }
        ]}
        fill={[
          {
            match: {
              id: 'ruby'
            },
            id: 'dots'
          },
          {
            match: {
              id: 'c'
            },
            id: 'dots'
          },
          {
            match: {
              id: 'go'
            },
            id: 'dots'
          },
          {
            match: {
              id: 'python'
            },
            id: 'dots'
          },
          {
            match: {
              id: 'scala'
            },
            id: 'lines'
          },
          {
            match: {
              id: 'lisp'
            },
            id: 'lines'
          },
          {
            match: {
              id: 'elixir'
            },
            id: 'lines'
          },
          {
            match: {
              id: 'javascript'
            },
            id: 'lines'
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
            itemWidth: 100,
            itemHeight: 18,
            itemTextColor: '#999',
            itemDirection: 'left-to-right',
            itemOpacity: 1,
            symbolSize: 18,
            symbolShape: 'circle',
            effects: [
              {
                on: 'hover',
                style: {
                  itemTextColor: '#000'
                }
              }
            ]
          }
        ]}
      />
    </div>
  );
};

export default DonutChart;
