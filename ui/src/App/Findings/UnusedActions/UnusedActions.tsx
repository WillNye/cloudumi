import { Segment } from 'shared/layout/Segment';
import { Table } from 'shared/elements/Table';
import { dataTable } from './mockData';
import { unusedPermissionsColumns } from './constants';
import { Button } from 'shared/elements/Button';
import { Divider } from 'shared/elements/Divider';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';
import { LineBreak } from 'shared/elements/LineBreak';
import styles from './UnusedActions.module.css';
import { useMemo } from 'react';
import Bullet from 'shared/elements/Bullet';
import { Card } from 'shared/layout/Card';
import ProgressBar from 'shared/elements/ProgressBar';

const UnusedActions = () => {
  const tableData = useMemo(
    () =>
      dataTable.map(data => {
        const account = data.accounts.length
          ? `${data.accounts[0].name} (${data.accounts[0].account})`
          : '';
        return {
          ...data,
          accounts: <div>{account}</div>,
          description: <Bullet color="danger" label={data.description} />
        };
      }),
    []
  );

  return (
    <Segment>
      <div className={styles.unusedActions}>
        <h3>Unused Cloud Actions</h3>
        <LineBreak size="small" />
        <Breadcrumbs
          items={[
            { name: 'Findings', url: '/findings' },
            { name: 'Unused Cloud Actions', url: '/findings/unused-actions' }
          ]}
        />
        <LineBreak />
        <Divider />
        <Segment className={styles.content}>
          <div className={styles.summary}>
            <div>
              <h4>UNUSED CLOUD ACTIONS BY RISK</h4>
              <div className={styles.progressUnit}>
                Critical
                <div className={styles.progressBar}>
                  <h5>0%</h5>
                  <ProgressBar color="danger" percentage={0} />
                </div>
              </div>
              <div className={styles.progressUnit}>
                High
                <div className={styles.progressBar}>
                  <h5>25.4%</h5>
                  <ProgressBar percentage={25.4} />
                </div>
              </div>
              <div className={styles.progressUnit}>
                Medium
                <div className={styles.progressBar}>
                  <h5>50%</h5>
                  <ProgressBar color="warning" percentage={50} />
                </div>
              </div>
            </div>
            <Divider orientation="vertical" />
            <div>
              <h4>OPEN FINDINGS BY RISK</h4>
              <LineBreak />
              <div className={styles.cardContainer}>
                <div className={styles.card}>
                  <h2>142</h2>
                  <LineBreak size="small" />
                  <p>Critical</p>
                </div>
                <div className={styles.card}>
                  <h2>142</h2>
                  <LineBreak size="small" />
                  <p>Critical</p>
                </div>
                <div className={styles.card}>
                  <h2>142</h2>
                  <LineBreak size="small" />
                  <p>Critical</p>
                </div>
                <div className={styles.card}>
                  <h2>142</h2>
                  <LineBreak size="small" />
                  <p>Critical</p>
                </div>
              </div>
            </div>
          </div>
          <LineBreak size="large" />
          <div className={styles.actions}>
            <h4>Actions:</h4>
            <div>
              <Button variant="text" disableAnimation>
                Dismiss
              </Button>
              <Button variant="text" disableAnimation>
                Request Remediation
              </Button>
              <Button variant="text" disableAnimation>
                File JIRA Ticket
              </Button>
              <Button variant="text" disableAnimation>
                Open in AWS
              </Button>
            </div>
          </div>
          <Table
            data={tableData}
            columns={unusedPermissionsColumns}
            showPagination
            enableRowSelection
            border="row"
            // spacing='compact'
          />
        </Segment>
      </div>
    </Segment>
  );
};

export default UnusedActions;
