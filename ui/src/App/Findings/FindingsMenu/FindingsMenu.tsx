import { Segment } from 'shared/layout/Segment';
import styles from './FindingsMenu.module.css';
import DonutChart from './components/DonutChart';
import LineChart from './components/LineChart';

const FindingsMenu = () => {
  return (
    <Segment>
      <div className={styles.findings}>
        <div className={styles.unusedItems}>
          <DonutChart />
          <DonutChart />
          <DonutChart />
          <DonutChart />
        </div>
        <div className={styles.cleanupProcess}>
          <LineChart />
          <LineChart />
        </div>
      </div>
    </Segment>
  );
};

export default FindingsMenu;
