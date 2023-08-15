import { ResponsiveLine } from '@nivo/line';
import { lineMockData } from './constants';

const LineChart = () => {
  return (
    <div style={{ height: 400, color: '#eee', position: 'relative' }}>
      <h3 style={{ color: '#eee', textAlign: 'left', marginLeft: '60px' }}>
        Unused Cloud Actions
      </h3>
      <select
        style={{
          position: 'absolute',
          top: '50px',
          right: '50px',
          background: '#333',
          color: '#eee',
          border: '1px solid #555'
        }}
        defaultValue="all-time"
      >
        <option value="all-time">For All Time</option>
        <option value="last-month">Last Month</option>
        <option value="last-quarter">Last Quarter</option>
        <option value="last-year">Last Year</option>
      </select>
      <p
        style={{
          color: 'green',
          textAlign: 'left',
          marginLeft: '60px',
          marginTop: '-10px'
        }}
      >
        85% less from when you first started using Noq
      </p>
      <ResponsiveLine
        data={lineMockData}
        margin={{ top: 50, right: 200, bottom: 50, left: 60 }}
        xScale={{ type: 'point' }}
        yScale={{
          type: 'linear',
          min: 'auto',
          max: 'auto',
          stacked: false,
          reverse: false
        }}
        axisTop={null}
        axisRight={null}
        axisBottom={{
          //   orient: "bottom",
          tickSize: 5,
          tickPadding: 5,
          tickRotation: 0,
          //   tickColor: "#696D77",
          legend: 'Month',
          legendOffset: 36,
          legendPosition: 'middle'
        }}
        axisLeft={{
          //   orient: "left",
          //   tickColor: "#696D77",
          tickSize: 5,
          tickPadding: 5,
          tickRotation: 0,
          legend: 'Count',
          legendOffset: -40,
          legendPosition: 'middle'
        }}
        colors={d => {
          switch (d.id) {
            case 'Unused actions':
              return 'red';
            case 'Dismissed actions':
              return '#C27565';
            default:
              return 'blue'; // default color, just in case
          }
        }}
        theme={{
          //   background: "#000",
          axis: {
            ticks: {
              text: {
                fill: '#878A96' // Color for labels
              }
            },
            legend: {
              text: {
                fill: '#878A96' // Color for axis legends
              }
            }
          },
          grid: {
            line: {
              stroke: '#33363F' // Set color for horizontal grid lines
            }
          },
          legends: {
            text: {
              fill: '#878A96' // Adjusting the color for legend labels
            }
          },
          tooltip: {
            container: {
              background: '#333'
            }
          }
        }}
        enableGridX={false}
        enableGridY={true}
        enablePoints={false} // Hide dots/points
        pointSize={10}
        pointColor={{ theme: 'background' }}
        pointBorderWidth={2}
        pointBorderColor={{ from: 'serieColor' }}
        pointLabelYOffset={-12}
        useMesh={true}
        legends={[
          {
            anchor: 'top-left',
            direction: 'row',
            justify: false,
            translateX: 10, // Reduced translateX value
            translateY: -30,
            itemsSpacing: 2,
            itemDirection: 'left-to-right',
            itemWidth: 140,
            itemHeight: 20,
            itemTextColor: '#878A96',
            itemOpacity: 0.75,
            symbolSize: 14,
            // symbolShape: LegendShape,
            symbolSpacing: 5,
            // symbolShape: "circle",
            symbolBorderColor: 'rgba(0, 0, 0, .5)',
            effects: [
              {
                on: 'hover',
                style: {
                  itemBackground: 'rgba(0, 0, 0, .03)',
                  itemOpacity: 1
                }
              }
            ]
          }
        ]}
        lineWidth={3}
      />
    </div>
  );
};

export default LineChart;
