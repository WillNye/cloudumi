import { ResponsiveLine } from '@nivo/line';
import { ResponsivePie } from '@nivo/pie';

const FindingsMenu = () => {
  // Generate mock data
  const currentDate = new Date();

  const generateDataPoint = (previousValue, trend = 'up') => {
    const randomChange = Math.floor(Math.random() * 10);
    if (trend === 'up') {
      return previousValue + randomChange;
    } else {
      return Math.max(previousValue - randomChange, 0);
    }
  };

  let previousUnusedValue = 100;
  let previousDismissedValue = 10;

  const data = [
    {
      id: 'Unused actions',
      data: Array.from({ length: 12 }, (_, i) => {
        const value = generateDataPoint(previousUnusedValue, 'down');
        previousUnusedValue = value;
        return {
          x: new Date(
            currentDate.getFullYear(),
            currentDate.getMonth() - i
          ).toLocaleDateString('en-US', { month: '2-digit', year: '2-digit' }),
          y: value
        };
      }).reverse()
    },
    {
      id: 'Dismissed actions',
      data: Array.from({ length: 12 }, (_, i) => {
        const value = generateDataPoint(previousDismissedValue, 'up');
        previousDismissedValue = value;
        return {
          x: new Date(
            currentDate.getFullYear(),
            currentDate.getMonth() - i
          ).toLocaleDateString('en-US', { month: '2-digit', year: '2-digit' }),
          y: value
        };
      }).reverse()
    }
  ];

  const LegendShape = ({ x, y, size, fill, borderWidth, borderColor }) => (
    <rect
      x={x - size / 2} // Adjusting x and y to center the rectangle
      y={y - size / 4} // Adjusting for half the height
      fill={fill}
      strokeWidth={borderWidth}
      stroke={borderColor}
      width={size / 2} // Adjusting width to be half of size
      height={size}
      rx={2} // Rounded corners
      style={{ pointerEvents: 'none' }}
    />
  );

  return (
    <div>
      <div style={{ height: 400, color: '#eee' }}>
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
        <ResponsivePie
          data={[
            {
              id: 'stylus',
              label: 'stylus',
              value: 153,
              color: 'hsl(195, 70%, 50%)'
            },
            {
              id: 'erlang',
              label: 'erlang',
              value: 187,
              color: 'hsl(171, 70%, 50%)'
            },
            {
              id: 'hack',
              label: 'hack',
              value: 40,
              color: 'hsl(253, 70%, 50%)'
            },
            {
              id: 'elixir',
              label: 'elixir',
              value: 225,
              color: 'hsl(65, 70%, 50%)'
            },
            {
              id: 'sass',
              label: 'sass',
              value: 419,
              color: 'hsl(117, 70%, 50%)'
            }
          ]}
          margin={{ top: 40, right: 80, bottom: 80, left: 80 }}
          innerRadius={0.5}
          padAngle={0.7}
          cornerRadius={3}
          activeOuterRadiusOffset={8}
          borderWidth={1}
          borderColor={{
            from: 'color',
            modifiers: [['darker', 0.2]]
          }}
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
        />{' '}
        <ResponsivePie
          data={[
            {
              id: 'stylus',
              label: 'stylus',
              value: 153,
              color: 'hsl(195, 70%, 50%)'
            },
            {
              id: 'erlang',
              label: 'erlang',
              value: 187,
              color: 'hsl(171, 70%, 50%)'
            },
            {
              id: 'hack',
              label: 'hack',
              value: 40,
              color: 'hsl(253, 70%, 50%)'
            },
            {
              id: 'elixir',
              label: 'elixir',
              value: 225,
              color: 'hsl(65, 70%, 50%)'
            },
            {
              id: 'sass',
              label: 'sass',
              value: 419,
              color: 'hsl(117, 70%, 50%)'
            }
          ]}
          margin={{ top: 40, right: 80, bottom: 80, left: 80 }}
          innerRadius={0.5}
          padAngle={0.7}
          cornerRadius={3}
          activeOuterRadiusOffset={8}
          borderWidth={1}
          borderColor={{
            from: 'color',
            modifiers: [['darker', 0.2]]
          }}
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
        />{' '}
        <ResponsivePie
          data={[
            {
              id: 'stylus',
              label: 'stylus',
              value: 153,
              color: 'hsl(195, 70%, 50%)'
            },
            {
              id: 'erlang',
              label: 'erlang',
              value: 187,
              color: 'hsl(171, 70%, 50%)'
            },
            {
              id: 'hack',
              label: 'hack',
              value: 40,
              color: 'hsl(253, 70%, 50%)'
            },
            {
              id: 'elixir',
              label: 'elixir',
              value: 225,
              color: 'hsl(65, 70%, 50%)'
            },
            {
              id: 'sass',
              label: 'sass',
              value: 419,
              color: 'hsl(117, 70%, 50%)'
            }
          ]}
          margin={{ top: 40, right: 80, bottom: 80, left: 80 }}
          innerRadius={0.5}
          padAngle={0.7}
          cornerRadius={3}
          activeOuterRadiusOffset={8}
          borderWidth={1}
          borderColor={{
            from: 'color',
            modifiers: [['darker', 0.2]]
          }}
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
        />{' '}
        <ResponsivePie
          data={[
            {
              id: 'stylus',
              label: 'stylus',
              value: 153,
              color: 'hsl(195, 70%, 50%)'
            },
            {
              id: 'erlang',
              label: 'erlang',
              value: 187,
              color: 'hsl(171, 70%, 50%)'
            },
            {
              id: 'hack',
              label: 'hack',
              value: 40,
              color: 'hsl(253, 70%, 50%)'
            },
            {
              id: 'elixir',
              label: 'elixir',
              value: 225,
              color: 'hsl(65, 70%, 50%)'
            },
            {
              id: 'sass',
              label: 'sass',
              value: 419,
              color: 'hsl(117, 70%, 50%)'
            }
          ]}
          margin={{ top: 40, right: 80, bottom: 80, left: 80 }}
          innerRadius={0.5}
          padAngle={0.7}
          cornerRadius={3}
          activeOuterRadiusOffset={8}
          borderWidth={1}
          borderColor={{
            from: 'color',
            modifiers: [['darker', 0.2]]
          }}
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
        <ResponsiveLine
          data={data}
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
              // y: {
              //   line: {
              //     stroke: "#33363F" // Set color for horizontal grid lines
              //   }
              // }
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
    </div>
  );
};

export default FindingsMenu;
