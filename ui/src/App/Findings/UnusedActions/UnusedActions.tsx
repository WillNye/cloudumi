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
import ProgressBar from 'shared/elements/ProgressBar';
import BarCharRating from 'shared/elements/BarCharRating';
import Tabs from 'shared/elements/Tabs';

// TODO: Replace content with UnusedActions component
const tabsData = [
  {
    label: 'Open (36)',
    content: <></>
  },
  {
    label: 'Pending (5)',
    content: <></>
  },
  {
    label: 'Dismissed (4)',
    content: <></>
  },
  {
    label: 'Resolved (123)',
    content: <></>
  }
];

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
        <Tabs tabs={tabsData} />
        <Segment className={styles.content}>
          <h5>IDENTITIES WITH UNUSED CLOUD ACTIONS</h5>
          <div className={styles.progressUnitWrapper}>
            <div className={styles.progressUnit}>
              <div className={styles.progressHeader}>
                <BarCharRating color="danger" activeBars={5} />
                Critical
              </div>
              <div className={styles.progressBar}>
                <h5>16.7%</h5>
                <ProgressBar color="danger" percentage={16.7} />
              </div>
              <LineBreak size="small" />
              <p>6/36</p>
            </div>
            <div className={styles.progressUnit}>
              <div className={styles.progressHeader}>
                <BarCharRating color="danger" activeBars={4} />
                High
              </div>
              <div className={styles.progressBar}>
                <h5>8.3%</h5>
                <ProgressBar color="danger" percentage={8.3} />
              </div>
              <LineBreak size="small" />
              <p>3/36</p>
            </div>
            <div className={styles.progressUnit}>
              <div className={styles.progressHeader}>
                <BarCharRating color="warning" activeBars={3} />
                Medium
              </div>
              <div className={styles.progressBar}>
                <h5>5.6%</h5>
                <ProgressBar color="warning" percentage={5.6} />
              </div>
              <LineBreak size="small" />
              <p>2/36</p>
            </div>
          </div>
          <div className={styles.actions}>
            <h4>Actions:</h4>
            <div>
              <Button variant="text" disableAnimation>
                Dismiss
              </Button>
              <Button variant="text" disableAnimation>
                Resolve with IAMbic Request
              </Button>
              <Button variant="text" disableAnimation>
                Create JIRA Ticket
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
