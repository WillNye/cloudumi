import { Fragment } from 'react';
import { Input } from 'shared/form/Input';
import { Select, SelectOption } from 'shared/form/Select';
import { TypeaheadBlock } from 'shared/form/TypeaheadBlock';
import { ChangeTypeField } from '../../types';

export type RequestFieldProps = {
  field: ChangeTypeField;
  selectedOptions: { [key: string]: string };
  handleChange: (key: string, value: string) => void;
};

const RequestField: React.FC<RequestFieldProps> = ({
  field,
  selectedOptions,
  handleChange
}) => {
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
        closeOnSelect={field.allow_multiple ? false : true}
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
        resultsFormatter={result => <p>{result.title}</p>}
        defaultValues={[]}
        handleOnSelectResult={value => {
          handleChange(field.field_key, value['title']);
        }}
        endpoint={field.typeahead.endpoint}
        queryParam={field.typeahead.query_param_key}
      />
    );
  }

  if (field.field_type === 'TypeAheadTemplateRef') {
    return (
      <TypeaheadBlock
        resultsFormatter={result => <p>{result.option_text}</p>}
        defaultValues={[]}
        handleOnSelectResult={value => {
          handleChange(field.field_key, value['option_value']);
        }}
        endpoint={field.typeahead.endpoint}
        queryParam={field.typeahead.query_param_key}
        titleKey="option_text"
      />
    );
  }
  return <Fragment />;
};

export type FieldType =
  | 'TypeAheadTemplateRef'
  | 'TypeAhead'
  | 'TextBox'
  | 'Choice';

export default RequestField;
