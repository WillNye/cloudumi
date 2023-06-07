import { useMemo, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './SelectChangeType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { Select } from '@noqdev/cloudscape';
import RequestChangeDetails from '../RequestChangeDetails';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getChangeRequestType } from 'core/API/iambicRequest';
import { Block } from 'shared/layout/Block';
import { ChangeType } from '../../types';
import { Divider } from 'shared/elements/Divider';
import { Button } from 'shared/elements/Button';
import { Table } from 'shared/elements/Table';

const SelectChangeType = () => {
  const [selectedChangeType, setSelectedChangeType] =
    useState<ChangeType | null>(null);
  const [changeTypes, setChangeTypes] = useState<ChangeType[]>([]);
  const {
    store: { selfServiceRequest },
    actions: { removeChange }
  } = useContext(SelfServiceContext);

  const selectedRequestType = useMemo(
    () => selfServiceRequest.requestType,
    [selfServiceRequest]
  );

  const { data, isLoading } = useQuery({
    queryFn: getChangeRequestType,
    queryKey: ['getChangeRequestType', selectedRequestType?.id],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    },
    onSuccess: ({ data }) => {
      setChangeTypes(data);
    }
  });

  const handleSelectChange = (detail: any) => {
    const selectedChange = changeTypes.find(
      changeType => changeType.id === detail.value
    );
    setSelectedChangeType(selectedChange);
    // Do something with the selected option
  };

  const options = changeTypes.map(changeType => ({
    label: changeType.name,
    value: changeType.id,
    description: changeType.description
  }));

  const tableRows = useMemo(
    () => selfServiceRequest.requestedChanges,
    [selfServiceRequest]
  );

  const changesColumns = useMemo(
    () => [
      {
        Header: 'Change Name',
        accessor: 'name',
        sortable: false
      },
      {
        Header: 'Description',
        accessor: 'description',
        sortable: true
      },
      // {
      //   Header: 'Field Changes',
      //   accessor: 'fields',
      //   sortable: false,
      //   Cell: ({ value }) => (
      //     <ul>
      //       {value.map(field => (
      //         <li key={field.field_key}>
      //           {field.field_key}: {field.value}
      //         </li>
      //       ))}
      //     </ul>
      //   )
      // },
      {
        Header: 'Actions',
        accessor: 'id',
        sortable: false,
        Cell: ({ row: { index } }) => {
          return (
            <Button
              onClick={() => removeChange(index)}
              color="secondary"
              size="small"
            >
              Remove
            </Button>
          );
        }
      }
    ],
    [removeChange]
  );

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Select Change Type</h3>
        <LineBreak />
        <p className={styles.subText}>Please select a change type</p>
        <LineBreak size="large" />
        <div className={styles.content}>
          <Block disableLabelPadding label="Change Type" />
          <Select
            selectedOption={
              selectedChangeType && {
                label: selectedChangeType.name,
                value: selectedChangeType.id,
                description: selectedChangeType.description
              }
            }
            onChange={({ detail }) => handleSelectChange(detail.selectedOption)}
            options={options}
            filteringType="auto"
            selectedAriaLabel="Selected"
          />
          <LineBreak size="large" />
          {/* TODO: May use a popup dialog for change details */}
          {selectedChangeType && (
            <RequestChangeDetails selectedChangeType={selectedChangeType} />
          )}
          <LineBreak size="large" />
          <h4>Selected Changes</h4>
          <LineBreak size="small" />
          <Table
            data={tableRows}
            columns={changesColumns}
            noResultsComponent={<div>Please add changes to the request</div>}
            border="row"
          />
        </div>
      </div>
    </Segment>
  );
};

export default SelectChangeType;
