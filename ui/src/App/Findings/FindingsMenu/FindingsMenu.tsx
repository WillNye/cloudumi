import { Segment } from 'shared/layout/Segment';
import styles from './FindingsMenu.module.css';
import DonutChart from './components/DonutChart';
import LineChart from './components/LineChart';
import SectionHeader from 'shared/elements/SectionHeader';
import { LineBreak } from 'shared/elements/LineBreak';
import { cleanupProgressMetricsData, unusedMetricsData } from './mockData';

const FindingsMenu = () => {
  return (
    <Segment>
      <div className={styles.findings}>
        <div className={styles.header}>
          <h3>Findings</h3>
          <div className={styles.lastScan}>Last scan: 07/22/2023 6:45PM</div>
        </div>
        <SectionHeader
          className={styles.sectionHeader}
          title="CURRENT STATE OF UNUSED ITEMS"
          size="small"
        />
        <div className={styles.unusedItems}>
          {unusedMetricsData.map(
            ({ data, title, labelDescription, labelTitle }, index) => (
              <DonutChart
                key={index}
                data={data}
                title={title}
                labelDescription={labelDescription}
                labelTitle={labelTitle}
              />
            )
          )}
        </div>
        <LineBreak />
        <SectionHeader
          className={styles.sectionHeader}
          title="CLEANUP PROGRESS "
          size="small"
        />
        <div className={styles.cleanupProcess}>
          <div className={styles.infoCard}>
            Noq has removed
            <p className={styles.highlight}> 540 </p>
            or 5% of all identities since start of usage
          </div>
          <div className={styles.lineCharts}>
            {cleanupProgressMetricsData.map(
              ({ title, description, data }, index) => (
                <LineChart
                  key={index}
                  data={data}
                  title={title}
                  description={description}
                />
              )
            )}
          </div>
        </div>
      </div>
    </Segment>
  );
};

export default FindingsMenu;
