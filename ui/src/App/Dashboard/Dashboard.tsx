import { Outlet } from 'react-router';
import { Navbar } from 'shared/elements/Navbar';
import styles from './Dashboard.module.css';

export const Dashboard = () => {
  return (
    <div className={styles.dashboard}>
      <Navbar />
      <main className={styles.mainContent}>
        <Outlet />
      </main>
    </div>
  );
};
