import { ResponsiveLine } from '@nivo/line';
import styles from './LineChart.module.css';

const LineChart = ({ data, description, title }) => {
  return (
    <div className={styles.lineChart}>
      <select className={styles.select} defaultValue="all-time">
        <option value="all-time">For All Time</option>
        <option value="last-month">Last Month</option>
        <option value="last-quarter">Last Quarter</option>
        <option value="last-year">Last Year</option>
      </select>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.description}>{description}</p>
      <div className={styles.wrapper}>
        <ResponsiveLine
          data={data}
          margin={{ top: 50, right: 50, bottom: 50, left: 50 }}
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
            tickSize: 5,
            tickPadding: 5,
            tickRotation: 0,
            legend: 'Month',
            legendOffset: 36,
            legendPosition: 'middle'
          }}
          axisLeft={{
            tickSize: 5,
            tickPadding: 5,
            tickRotation: 0,
            legend: 'Count',
            legendOffset: -40,
            legendPosition: 'middle'
          }}
          colors={d => {
            switch (d.id) {
              case 'unused_actions':
                return 'red';
              case 'dismissed_actions':
                return '#C27565';
              default:
                return 'blue'; // default color, just in case
            }
          }}
          theme={{
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
          enablePoints={false}
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
              translateX: 10,
              translateY: -30,
              itemsSpacing: 2,
              itemDirection: 'left-to-right',
              itemWidth: 140,
              itemHeight: 20,
              itemTextColor: '#878A96',
              itemOpacity: 0.75,
              symbolSize: 10,
              symbolSpacing: 5
            }
          ]}
          lineWidth={3}
        />
      </div>
    </div>
  );
};

export default LineChart;
