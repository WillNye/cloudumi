import { Segment } from 'shared/layout/Segment';
import styles from './FindingsMenu.module.css';
import DonutChart from './components/DonutChart';
import LineChart from './components/LineChart';
import SectionHeader from 'shared/elements/SectionHeader';
import { LineBreak } from 'shared/elements/LineBreak';

const FindingsMenu = () => {
  return (
    <Segment>
      <h4>Findings</h4>
      <LineBreak />
      <div className={styles.findings}>
        <SectionHeader
          className={styles.sectionHeader}
          title="CURRENT STATE OF UNUSED ITEMS"
          size="small"
        />
        <div className={styles.unusedItems}>
          <DonutChart />
          <DonutChart />
          <DonutChart />
          <DonutChart />
        </div>
        <LineBreak />
        <SectionHeader
          className={styles.sectionHeader}
          title="CLEANUP PROGRESS "
          size="small"
        />
        <div className={styles.cleanupProcess}>
          <LineChart />
          <LineChart />
        </div>
      </div>
    </Segment>
  );
};

export default FindingsMenu;
