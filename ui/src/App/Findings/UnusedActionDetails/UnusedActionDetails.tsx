import { Segment } from 'shared/layout/Segment';
import { LineBreak } from 'shared/elements/LineBreak';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';
import { Divider } from 'shared/elements/Divider';
import { Button } from 'shared/elements/Button';
import styles from './UnusedActionDetails.module.css';
import { Table } from 'shared/elements/Table';
import { unusedActionsColumns } from './constants';
import { dataTable, newTemplate, oldTemplate } from './mockData';
import { DiffEditor } from 'shared/form/DiffEditor';
import { Chip } from 'shared/elements/Chip';
import Bullet from 'shared/elements/Bullet';

const UnusedActionDetails = () => {
  return (
    <Segment>
      <div className={styles.actionDetails}>
        <h3>MonitoringServiceRole</h3>
        <LineBreak size="small" />
        <Breadcrumbs
          items={[
            { name: 'Findings', url: '/findings' },
            { name: 'Unused Cloud Actions', url: '/findings/unused-actions' },
            { name: 'MonitoringServiceRole', url: '/findings/unused-actions/' }
          ]}
        />
        <LineBreak />
        <div className={styles.header}>
          <div>
            <Chip type="primary">Open</Chip>
            <LineBreak size="small" />
            <Bullet color="danger" label={<h4>MonitoringServiceRole</h4>} />
          </div>
          <div className={styles.headerActions}>
            <Button size="small" variant="outline">
              Dismiss
            </Button>
            <Button size="small">Create Request to Resolve Finding</Button>
            <Button size="small">Create JIRA Ticket</Button>
          </div>
        </div>
        <Divider />
        <LineBreak />
        <div className={styles.wrapper}>
          <div className={styles.contentTable}>
            <Table
              columns={unusedActionsColumns}
              data={dataTable}
              border="row"
            />
            <LineBreak size="large" />
            <h3>Unused Actions</h3>
          </div>
          <div className={styles.codeEditor}>
            <DiffEditor
              original={oldTemplate}
              modified={newTemplate}
              readOnly={true}
            />
          </div>
        </div>
      </div>
    </Segment>
  );
};

export default UnusedActionDetails;
