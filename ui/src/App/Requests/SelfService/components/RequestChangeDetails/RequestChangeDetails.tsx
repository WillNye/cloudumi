import { useEffect, useState, useMemo, useContext } from 'react';
import { Table } from 'shared/elements/Table';
import { Button } from 'shared/elements/Button';
import axios from 'axios';

import SelfServiceContext from '../../SelfServiceContext';
import { LineBreak } from 'shared/elements/LineBreak';
import { Block } from 'shared/layout/Block';
import RequestField from './RequestField';
import { ChangeTypeDetails } from '../../types';

interface SelectedOptions {
  [key: string]: string;
}

const RequestChangeDetails = () => {
  const {
    store: { selectedChangeType, requestedChanges },
    actions: { addChange, removeChange }
  } = useContext(SelfServiceContext);

  const [changeTypeDetails, setChangeTypeDetails] =
    useState<ChangeTypeDetails | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<SelectedOptions>({});

  const handleChange = (fieldKey: string, value: string) => {
    setSelectedOptions(prev => ({ ...prev, [fieldKey]: value }));
  };

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
      {
        Header: 'Field Changes',
        accessor: 'fields',
        sortable: false,
        Cell: ({ value }) => (
          <ul>
            {value.map(field => (
              <li key={field.field_key}>
                {field.field_key}: {field.value}
              </li>
            ))}
          </ul>
        )
      },
      {
        Header: 'Actions',
        accessor: 'id',
        sortable: false,
        Cell: ({ rowIndex }) => (
          <Button onClick={() => removeChange(rowIndex)}>Remove</Button>
        )
      }
    ],
    [removeChange]
  );

  const tableRows = useMemo(() => {
    return requestedChanges;
  }, [requestedChanges]);

  useEffect(() => {
    if (selectedChangeType) {
      axios
        .get(
          `/api/v4/self-service/request-types/${selectedChangeType.request_type_id}` +
            `/change-types/${selectedChangeType.id}`
        )
        .then(res => {
          setChangeTypeDetails(res.data?.data);
          console.log(changeTypeDetails);
        })
        .catch(err => {
          console.error(err);
        });
    }
  }, [selectedChangeType, changeTypeDetails]);

  const handleSubmit = e => {
    e.preventDefault();
    addChange({
      id: changeTypeDetails.id,
      name: changeTypeDetails.name,
      description: changeTypeDetails.description,
      request_type_id: changeTypeDetails.request_type_id,
      fields: changeTypeDetails.fields.map(field => ({
        ...field,
        value: selectedOptions[field.field_key]
      }))
    });
    setSelectedOptions({});
  };

  return (
    <form onSubmit={handleSubmit}>
      {changeTypeDetails?.fields?.map(field => (
        <div key={field.id}>
          <Block
            disableLabelPadding
            key={field.field_key}
            label={field.field_text}
          ></Block>
          <RequestField
            selectedOptions={selectedOptions}
            handleChange={handleChange}
            field={field}
          />
          <LineBreak />
        </div>
      ))}
      <Button color="secondary" type="submit" size="small">
        Add Change
      </Button>
    </form>
  );
};

export default RequestChangeDetails;
