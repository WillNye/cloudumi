import { Fragment } from 'react';
import { Input } from 'shared/form/Input';
import { Select, SelectOption } from 'shared/form/Select';
import { TypeaheadBlock } from 'shared/form/TypeaheadBlock';

const RequestField = ({ field, selectedOptions, handleChange }) => {
  console.log(field, '-----------------');

  if (field.field_type === 'TextBox') {
    return (
      <Input
        type="text"
        size-="small"
        id={field.field_key}
        name={field.field_key}
        placeholder={field.field_key}
        value={selectedOptions[field.field_key] || ''}
        required={!field.allow_none}
        onChange={e => handleChange(field.field_key, e.target.value)}
      />
    );
  }
  if (field.field_type === 'Choice') {
    return (
      <Select
        id={field.field_key}
        name={field.field_key}
        placeholder="Select from the list below"
        value={selectedOptions[field.field_key] || ''}
        onChange={value => handleChange(field.field_key, value)}
        multiple={field.allow_multiple}
        required={!field.allow_none && !selectedOptions[field.field_key]}
      >
        {field.options?.map(option => (
          <SelectOption key={option} value={option}>
            {option}
          </SelectOption>
        ))}
      </Select>
    );
  }
  if (field.field_type === 'TypeAhead') {
    return (
      <TypeaheadBlock
        defaultValue={selectedOptions[field.field_key] || ''}
        handleInputUpdate={(value: string) =>
          handleChange(field.field_key, value)
        }
        resultsFormatter={result => <p>{result.title}</p>}
        // resultsFormatter={value => ({ title: value })} // Use your own formatter if needed
        defaultValues={[]}
        endpoint={field.typeahead.endpoint}
        queryParam={field.typeahead.query_param_key}
      />
    );
  }
  return <Fragment />;
};

export default RequestField;
