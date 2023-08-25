import { Segment } from 'shared/layout/Segment';
import { LineBreak } from 'shared/elements/LineBreak';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';
import { Divider } from 'shared/elements/Divider';
import { Button } from 'shared/elements/Button';
import styles from './UnusedActionDetails.module.css';
import { Table } from 'shared/elements/Table';
import { unusedActionsColumns, unusedServicesColumns } from './constants';
import {
  dataTable,
  newTemplate,
  oldTemplate,
  unusedActionsList
} from './mockData';
import { DiffEditor } from 'shared/form/DiffEditor';
import { Chip } from 'shared/elements/Chip';
import Bullet from 'shared/elements/Bullet';
import { useMemo } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Select, SelectOption } from 'shared/form/Select';
import BarCharRating from 'shared/elements/BarCharRating';

const UnusedActionDetails = () => {
  const unusedActionData = useMemo(() => {
    return unusedActionsList.map(unusedAction => {
      return {
        resource_identity: unusedAction.resource,
        severity: `${unusedAction.actions?.length} unused`,
        last_accessed: 'Service last accessed',
        subRows: unusedAction.actions.map(action => ({
          ...action,
          severity: <BarCharRating activeBars={5} color="danger" />
        }))
      };
    });
  }, []);

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
            <div className={styles.headerActions}>
              <div>
                <BarCharRating activeBars={5} color="danger" />
                <h3>Unused Actions</h3>
              </div>
              <Button variant="text">
                <Icon size="medium" name="export" />
                Export
              </Button>
            </div>
            <Divider />
            <div className={styles.headerActions}>
              <h4 className={styles.lastScan}>SERVICE</h4>
              <div className={styles.selectInput}>
                <Select value="prod">
                  <SelectOption value="prod">Prod</SelectOption>
                </Select>
              </div>
            </div>
            <LineBreak />
            <Table
              border="column"
              enableExpanding
              data={unusedActionData}
              columns={unusedServicesColumns}
              hideTableHeader
            />
          </div>

          <div className={styles.codeEditor}>
            <p>
              You can override any findings in Code Editor before creating the
              request{' '}
            </p>
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
