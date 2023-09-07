import styles from './RequestPreview.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { Table } from 'shared/elements/Table';
import { Segment } from 'shared/layout/Segment';

const RequestSummary = () => {
  const {
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);
  return (
    <Segment className={styles.summary}>
      <LineBreak />
      <Table
        border="row"
        spacing="expanded"
        columns={[
          {
            accessorKey: 'key'
          },
          {
            accessorKey: 'value'
          }
        ]}
        hideTableHeader
        data={[
          { key: 'Cloud Provider', value: selfServiceRequest.provider },
          { key: 'Request Type', value: selfServiceRequest?.requestType?.name },
          {
            key: 'Identity',
            value: selfServiceRequest?.identity?.template_type
          },
          {
            key: 'Changes',
            value: (
              <div>
                <Table
                  data={selfServiceRequest.requestedChanges}
                  hideTableHeader
                  columns={[
                    {
                      header: 'Change Name',
                      accessorKey: 'name'
                    },
                    {
                      header: 'Description',
                      accessorKey: 'description'
                    }
                  ]}
                  border="column"
                  spacing="compact"
                />
              </div>
            )
          },
          {
            key: 'Expires',
            value: selfServiceRequest?.expirationDate ?? 'Never'
          },
          { key: 'Justification', value: selfServiceRequest?.justification }
        ]}
      />
    </Segment>
  );
};

export default RequestSummary;
