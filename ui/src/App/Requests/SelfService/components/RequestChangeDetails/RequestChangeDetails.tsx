import {
  ChangeEvent,
  FormEvent,
  useEffect,
  useState,
  useMemo,
  useContext
} from 'react';
import { Select, SelectOption } from 'shared/form/Select';
import { Table } from 'shared/elements/Table';
import { Button } from 'shared/elements/Button';
import axios from 'axios';

import SelfServiceContext, {
  ChangeType,
  ChangeTypeField,
  ChangeTypeDetails
} from '../../SelfServiceContext';
import { TypeaheadBlock } from 'shared/form/TypeaheadBlock';

interface SelectedOptions {
  [key: string]: string;
}

interface RequestChangeDetailsProps {
  selectedChangeType: ChangeType;
  addChange: (change: ChangeTypeDetails) => void;
  requestedChanges: ChangeTypeDetails[];
  removeChange: (index: number) => void;
}

const RequestChangeDetails = () => {
  const {
    store: { selectedChangeType, requestedChanges },
    actions: { addChange, removeChange, goBack }
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
  }, [selectedChangeType]);

  const renderField = field => {
    switch (field.field_type) {
      case 'TextBox':
        return (
          <input
            type="text"
            id={field.field_key}
            name={field.field_key}
            value={selectedOptions[field.field_key] || ''}
            onChange={e => handleChange(field.field_key, e.target.value)}
          />
        );
      case 'Choice':
        return (
          <Select
            id={field.field_key}
            name={field.field_key}
            value={selectedOptions[field.field_key] || ''}
            onChange={value => handleChange(field.field_key, value)}
          >
            {field.options?.map(option => (
              <SelectOption key={option} value={option}>
                {option}
              </SelectOption>
            ))}
          </Select>
        );
      case 'TypeAhead':
        return null;
      //   <TypeaheadBlock
      //     defaultValue={selectedOptions[field.field_key] || ''}
      //     handleInputUpdate={(value: string) => handleChange(field.field_key, value)}
      //     resultsFormatter={(value) => ({ title: value })} // Use your own formatter if needed
      //   />
      default:
        return null;
    }
  };

  const handleSubmit = async e => {
    e.preventDefault();
    await addChange({
      id: changeTypeDetails.id,
      name: changeTypeDetails.name,
      description: changeTypeDetails.description,
      request_type_id: changeTypeDetails.request_type_id,
      fields: changeTypeDetails.fields.map(field => ({
        ...field,
        value: selectedOptions[field.field_key]
      }))
    });
    alert('Added Change: ' + JSON.stringify(selectedOptions, null, 2));
    setSelectedOptions({});
  };

  return (
    <form onSubmit={handleSubmit}>
      {changeTypeDetails?.fields?.map(field => (
        <div key={field.id}>
          <label htmlFor={field.field_key}>{field.field_text}</label>
          {renderField(field)}
        </div>
      ))}
      <Button onClick={goBack}>Back</Button>
      <Button type="submit">Add Change</Button>
      {/* TODO: we want a table of changes that users can add to / remove from before they go to the review page
        <Table
            data={tableRows}
            columns={changesColumns}
            border="row"
            isLoading={false}
        /> */}
    </form>
  );
};

export default RequestChangeDetails;
