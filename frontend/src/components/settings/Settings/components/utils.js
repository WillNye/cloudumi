/* eslint-disable react-hooks/exhaustive-deps */
import React,  { useEffect } from 'react'
import { Button, Input, Form } from 'semantic-ui-react'
import { Fill, Bar } from 'lib/Misc'
import { useApi } from 'hooks/useApi';

export const SelectAccount = ({ register, label, name, options = [] }) => {

  const { get } = useApi('services/aws/account/spoke');

  useEffect(() => {
    get.do();
    return () => {
      get.reset();
    }
  }, []);

  const handleOptions = (data) => {
    if (data) return data.map(i => `${i.name} - ${i.account_id}`);
    return options;
  };

  const isLoading = get?.status === 'working';

  const isDone = get?.status === 'done';

  const isEmpty = isDone && get.empty;

  return (
    <Form.Field>
      <label>{label}</label>
      <select {...register} disabled={isLoading || isEmpty}>
        {isEmpty && <option value="">You need at least one Soke Account to proceed!</option>}
        {!isLoading && <option value="">Select one account</option>}
        {!isLoading ? handleOptions(get?.data).map((value, index) => (  
          <option key={index} value={value}>
            {value}
          </option>
        )) : <option value="">Loading accounts...</option>}
      </select>
    </Form.Field>
  )
};

export const SectionTitle = ({ title, helpHandler }) => {
  const handleHelpModal = (handler) => {}

  return (
    <>
      <span>{title}</span>&nbsp;
      {helpHandler && (
        <Button
          size='mini'
          circular
          icon='question'
          basic
          onClick={() => handleHelpModal(helpHandler)}
        />
      )}
    </>
  )
}

export const TableTopBar = ({ onSearch, onClick, disabled, extras }) => {
  return (
    <Bar>
      {onSearch && (
        <Input
          size='small'
          label='Search'
          icon='search'
          disabled={disabled}
          onChange={onSearch}
        />
      )}
      <Fill />
      {extras}
      {onClick && (
        <Button
          compact
          color='blue'
          onClick={onClick}
          disabled={disabled}
          style={{ marginRight: 0 }}
        >
          New
        </Button>
      )}
    </Bar>
  )
}
