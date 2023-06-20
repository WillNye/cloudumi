import { useCallback, useEffect, useMemo, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './SelectChangeType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import RequestChangeDetails from '../RequestChangeDetails';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import {
  getChangeRequestType,
  getProviderDefinitions
} from 'core/API/iambicRequest';
import { Divider } from 'shared/elements/Divider';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { ChangeType } from '../../types';
import { Button } from 'shared/elements/Button';
import { Table } from 'shared/elements/Table';
import {
  Select as CloudScapeSelect,
  DatePicker,
  TimeInput
} from '@noqdev/cloudscape';
import { TextArea } from 'shared/form/TextArea';
import { Radio } from 'shared/form/Radio';
import { Select, SelectOption } from 'shared/form/Select';
import { addDays, format } from 'date-fns';

const SelectChangeType = () => {
  const [selectedChangeType, setSelectedChangeType] =
    useState<ChangeType | null>(null);
  const {
    store: {
      selfServiceRequest,
      expirationType,
      relativeValue,
      relativeUnit,
      dateValue,
      timeValue
    },
    actions: {
      removeChange,
      setJustification,
      setExpirationType,
      setRelativeValue,
      setRelativeUnit,
      setDateValue,
      setTimeValue
    }
  } = useContext(SelfServiceContext);

  const handleDurationTypeChange = useCallback(e => {
    setExpirationType(e.target.value);
    if (e.target.value === 'never') {
      setRelativeValue('');
      setDateValue('');
      setTimeValue('');
    }
  }, []);

  // Default expiration should be set to "Relative" and "5 days"
  useEffect(() => {
    if (!expirationType) {
      setExpirationType('relative');
      setRelativeValue('5');
      setRelativeUnit('Days');

      const futureDate = format(addDays(new Date(), 5), 'yyyy/MM/dd');
      setDateValue(futureDate);
      setTimeValue('00:00:00');
    }
  }, [expirationType]);

  const { data: providerDefinition, isLoading: loadingDefinitions } = useQuery({
    queryFn: getProviderDefinitions,
    queryKey: [
      'getProviderDefinitions',
      {
        provider: selfServiceRequest?.provider,
        template_id: selfServiceRequest?.identity
          ? selfServiceRequest.identity?.id
          : null
      }
    ],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    }
  });

  const selectedRequestType = useMemo(
    () => selfServiceRequest.requestType,
    [selfServiceRequest]
  );

  const { data: changeTypes, isLoading } = useQuery({
    queryFn: getChangeRequestType,
    queryKey: ['getChangeRequestType', selectedRequestType?.id],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    }
  });

  const handleSelectChange = (detail: any) => {
    const selectedChange = changeTypes?.data.find(
      changeType => changeType.id === detail.value
    );
    setSelectedChangeType(selectedChange);
    // Do something with the selected option
  };

  const options = useMemo(
    () =>
      changeTypes?.data?.map(changeType => ({
        label: changeType.name,
        value: changeType.id,
        description: changeType.description
      })),
    [changeTypes]
  );

  const tableRows = useMemo(
    () => selfServiceRequest.requestedChanges,
    [selfServiceRequest]
  );

  const changesColumns = useMemo(
    () => [
      {
        header: 'Change Name',
        accessorKey: 'name',
        sortable: false
      },
      {
        header: 'Description',
        accessorKey: 'description',
        sortable: true
      },
      // {
      //   header: 'Field Changes',
      //   accessorKey: 'fields',
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
        header: 'Actions',
        accessorKey: 'id',
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
          <CloudScapeSelect
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
            placeholder="Select change type"
          />
          <LineBreak size="large" />
          {selectedChangeType && (
            <RequestChangeDetails
              selectedChangeType={selectedChangeType}
              providerDefinition={providerDefinition?.data || []}
            />
          )}
          {tableRows.length > 0 && (
            <>
              <LineBreak size="large" />
              <h4>Selected Changes</h4>
              <LineBreak size="small" />
              <Table
                data={tableRows}
                columns={changesColumns}
                noResultsComponent={
                  <div className={styles.subText}>
                    Please add changes to the request
                  </div>
                }
                border="row"
              />
            </>
          )}
        </div>
        {tableRows.length > 0 && (
          <>
            <LineBreak size="large" />
            <Block disableLabelPadding label="Expiration" />
            <div className={styles.radioGroup}>
              <div className={styles.radioInput}>
                <Radio
                  name="durationType"
                  value="relative"
                  checked={expirationType === 'relative'}
                  onChange={handleDurationTypeChange}
                />
                <div>Relative</div>
              </div>

              <div className={styles.radioInput}>
                <Radio
                  name="durationType"
                  value="absolute"
                  checked={expirationType === 'absolute'}
                  onChange={handleDurationTypeChange}
                />
                <div>Absolute</div>
              </div>

              <div className={styles.radioInput}>
                <Radio
                  name="durationType"
                  value="never"
                  checked={expirationType === 'never'}
                  onChange={handleDurationTypeChange}
                />
                <div>Never</div>
              </div>
            </div>
            <LineBreak size="small" />
            <Divider />
            <LineBreak size="small" />
            {expirationType === 'relative' && (
              <div className={styles.relative}>
                <Input
                  type="number"
                  value={relativeValue}
                  onChange={e => setRelativeValue(e.target.value)}
                  fullWidth
                />
                <LineBreak size="small" />
                <Select
                  value={relativeUnit}
                  onChange={value => setRelativeUnit(value)}
                  name="time"
                >
                  <SelectOption value="Hours">Hours</SelectOption>
                  <SelectOption value="Days">Days</SelectOption>
                  <SelectOption value="Weeks">Weeks</SelectOption>
                  <SelectOption value="Months">Months</SelectOption>
                </Select>
              </div>
            )}
            {expirationType === 'absolute' && (
              <div className={styles.absolute}>
                <DatePicker
                  placeholder="YYYY/MM/DD"
                  value={dateValue}
                  onChange={({ detail: { value } }) => setDateValue(value)}
                  ariaLabelledby="duration-date-label"
                  previousMonthAriaLabel="Previous month"
                  nextMonthAriaLabel="Next month"
                  todayAriaLabel="Today"
                />
                <TimeInput
                  ariaLabelledby="duration-time-label"
                  use24Hour={true}
                  placeholder="hh:mm:ss"
                  value={timeValue}
                  onChange={({ detail: { value } }) => setTimeValue(value)}
                />
              </div>
            )}
            <LineBreak size="large" />
            <Block disableLabelPadding label="Justification" />
            <TextArea
              fullWidth
              value={selfServiceRequest.justification}
              onChange={e => setJustification(e.target.value)}
            />
          </>
        )}
      </div>
    </Segment>
  );
};

export default SelectChangeType;
