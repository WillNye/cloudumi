import { ResponsivePie } from '@nivo/pie';
import styles from './DonutChart.module.css';
import { Icon } from 'shared/elements/Icon';
import { Tooltip } from 'shared/elements/Tooltip';
import { CenteredMetric, CustomTooltip } from './Overrides';

const customColors = ['#EA3710', '#16B7CD', '#C27565'];

const DonutChart = ({ data, title, labelDescription, labelTitle }) => {
  return (
    <div className={styles.donutChart}>
      <h4 className={styles.title}>
        <span>{title}</span>

        <Tooltip text={title}>
          <Icon name="info" size="medium" />
        </Tooltip>
      </h4>
      <div className={styles.wrapper}>
        <ResponsivePie
          data={data}
          margin={{ top: 30, bottom: 60 }}
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
            props => (
              <CenteredMetric
                {...props}
                labelDescription={labelTitle}
                labelTitle={labelDescription}
              />
            )
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
          tooltip={CustomTooltip}
        />
      </div>
    </div>
  );
};

export default DonutChart;
