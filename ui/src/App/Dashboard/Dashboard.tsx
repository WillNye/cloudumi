import { Outlet } from 'react-router';
import { Navbar } from 'shared/elements/Navbar';
import styles from './Dashboard.module.css';

export const Dashboard = () => {
  return (
    <div className={styles.dashboard}>
      <Navbar />
      <div className={styles.content}>
        <Outlet />
      </div>
    </div>
  );
};
