import { Button } from 'shared/elements/Button';
import { Card } from 'shared/layout/Card';
import styles from './RequestsMenu.module.css';
import { Segment } from 'shared/layout/Segment';
import { useState } from 'react';
import { REQUESTS_SECTIONS, recentRequestsColumns } from './constants';
import { LineBreak } from 'shared/elements/LineBreak';
import { Divider } from 'shared/elements/Divider';
import { Table } from 'shared/elements/Table';
import { Icon } from 'shared/elements/Icon';
import { useNavigate } from 'react-router-dom';
import awsIcon from '../../../assets/integrations/awsIcon.svg';

const RequestsMenu = () => {
  const [currentTab, setCurrentTab] = useState(
    REQUESTS_SECTIONS.RECENT_REQUESTS
  );

  const navigate = useNavigate();

  return (
    <div className={styles.wrapper}>
      <Segment>
        <div className={styles.header}>
          <h3>Requests</h3>

          <div className={styles.btnActions}>
            <Button
              size="small"
              onClick={() => {
                navigate('/requests/create');
              }}
            >
              <Icon name="add" /> Create Request
            </Button>
            <Divider orientation="vertical" />
            <Button
              size="small"
              color="secondary"
              onClick={() => {
                navigate('/requests/all');
              }}
            >
              View All Requests
            </Button>
          </div>
        </div>
        <LineBreak size="large" />
        <p>
          IAMbic is a multi-cloud IAM control plane that centralizes and
          simplifies access management, providing a human-readable
          representation of IAM in version control. Request access and
          streamline your cloud permissions today.
        </p>
        <LineBreak size="large" />
        <h3>Recently Accessed Providers</h3>
        <LineBreak />
        <Card variant="outlined" color="primary">
          <div>
            <img className={styles.cardImg} src={awsIcon} />
            <p>AWS</p>
          </div>
        </Card>

        <LineBreak />
        <Divider />
        <LineBreak />
        <div>
          <nav className={styles.nav}>
            <ul className={styles.navList}>
              <li
                className={`${styles.navItem} ${
                  currentTab === REQUESTS_SECTIONS.RECENT_REQUESTS
                    ? styles.isActive
                    : ''
                }`}
                onClick={() => setCurrentTab(REQUESTS_SECTIONS.RECENT_REQUESTS)}
              >
                <div className={styles.text}>Recent Requests</div>
              </li>
              <li
                className={`${styles.navItem} ${
                  currentTab === REQUESTS_SECTIONS.MY_REQUESTS
                    ? styles.isActive
                    : ''
                }`}
                onClick={() => setCurrentTab(REQUESTS_SECTIONS.MY_REQUESTS)}
              >
                <div className={styles.text}>My Requests</div>
              </li>
            </ul>
          </nav>
          <LineBreak />

          <Table data={[]} columns={recentRequestsColumns} border="row" />
        </div>
      </Segment>
    </div>
  );
};

export default RequestsMenu;
