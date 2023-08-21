import { Segment } from 'shared/layout/Segment';
import styles from './UnusedActions.module.css';
import { Table } from 'shared/elements/Table';
import { dataTable } from './mockData';
import { unusedPermissionsColumns } from './constants';
import { Button } from 'shared/elements/Button';
import { Divider } from 'shared/elements/Divider';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';

const UnusedActions = () => {
  return (
    <Segment>
      <h3>Unused Cloud Actions</h3>
      <Breadcrumbs
        items={[
          { name: 'Findings', url: '/findings' },
          { name: 'Unused Cloud Actions', url: '/findings/unused-actions' }
        ]}
      />
      <div>
        <div>
          <h4>UNUSED CLOUD ACTIONS BY RISK</h4>
        </div>
        <Divider orientation="vertical" />
        <div>
          <h4>OPEN FINDINGS BY RISK</h4>
          <p>
            <span>14</span> Critical Open Findings
          </p>
          <p>
            <span>11</span> Medium Open Findings
          </p>
          <p>
            <span>25</span> Total Open Findings
          </p>
        </div>
      </div>
      <div>
        Actions:
        <div>
          <Button variant="text">Dismiss</Button>
          <Button variant="text">Request Remediation</Button>
          <Button variant="text">File JIRA Ticket</Button>
          <Button variant="text">Open in AWS</Button>
        </div>
      </div>
      <Table
        data={dataTable}
        columns={unusedPermissionsColumns}
        showPagination
        enableRowSelection
        border="row"
      />
    </Segment>
  );
};

export default UnusedActions;
