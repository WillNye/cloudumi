import { useCallback, useMemo, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './SelectChangeType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import RequestChangeDetails from '../RequestChangeDetails';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { DateTime } from 'luxon';
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
  Tabs,
  TimeInput
} from '@noqdev/cloudscape';
import { TextArea } from 'shared/form/TextArea';
import { Radio } from 'shared/form/Radio';
import { Select, SelectOption } from 'shared/form/Select';
import { EXPIRATION_TYPE, SELF_SERVICE_STEPS } from '../../constants';
import { Card } from 'shared/layout/Card';

const SUGGESTED_CHANGES = [
  {
    header: 'Base Application Policy',
    subtext: 'Provides access to essential services like S3, RDS, and EC2.'
  },
  {
    header: 'Lambda with EventBridge',
    subtext: 'Lambda Permissions with EventBridge'
  },
  {
    header: 'App-Specific Lambda',
    subtext:
      'Create, update, and manage a Lambda function specific to the application.'
  },
  {
    header: 'Create/Manage KMS-Encrypted S3 Bucket',
    subtext:
      'Allows creating and managing an S3 bucket encrypted with AWS Key Management Service (KMS).'
  },
  {
    header: 'Manage SQS and SNS',
    subtext:
      'Enables creating, sending, receiving, and managing messages in SQS queues and SNS topics.'
  },
  {
    header: 'Access to Cyberdyne Data (S3/Glue)',
    subtext:
      'Provides access to Cyberdyne Data, including S3 buckets and AWS Glue data catalog.'
  },
  {
    header: 'Manage DynamoDB Tables',
    subtext:
      'Allows creating, updating, and deleting DynamoDB tables for the application.'
  },
  {
    header: 'Manage CloudFormation Stacks',
    subtext:
      'Enables creating, updating, and deleting CloudFormation stacks for deploying application resources.'
  },
  {
    header: 'Manage Redshift Clusters',
    subtext:
      'Ability to create, modify, and delete Amazon Redshift clusters for data warehousing.'
  },
  {
    header: 'Manage EMR Clusters',
    subtext:
      'Enables starting, stopping, and terminating Amazon EMR clusters for big data processing.'
  }
];

const SelectChangeType = () => {
  const [selectedChangeType, setSelectedChangeType] =
    useState<ChangeType | null>(null);
  const {
    actions: { setCurrentStep }
  } = useContext(SelfServiceContext);
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
      setTimeValue,
      setExpirationDate
    }
  } = useContext(SelfServiceContext);

  const setExpirationFromAbsoluteDate = useCallback(
    (dateValue, time) => {
      const date = DateTime.fromISO(dateValue);
      const [hours, minutes] = time.split(':').map(Number);
      const newDateTime = date.plus({ hours, minutes });
      const formattedDateTime = newDateTime.toFormat('yyyy/MM/dd HH:mm ZZZZ');
      setExpirationDate(formattedDateTime);
    },
    [setExpirationDate]
  );

  const setExpirationFromRelativeate = useCallback(
    (time, units) => {
      setExpirationDate(`In ${time} ${units}`);
    },
    [setExpirationDate]
  );

  const handleDurationTypeChange = useCallback(
    e => {
      const value = e.target.value;
      setExpirationType(value);
      if (value === EXPIRATION_TYPE.ABSOLUTE) {
        setExpirationFromAbsoluteDate(dateValue, timeValue);
      } else if (value === EXPIRATION_TYPE.RELATIVE) {
        setExpirationFromRelativeate(relativeValue, relativeUnit);
      } else {
        setExpirationDate(null);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [dateValue, timeValue, relativeValue, relativeUnit]
  );

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
        sortable: false,
        accessorFn: (_data, index: number) => {
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
      <div className={styles.content}>
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
                  value={EXPIRATION_TYPE.RELATIVE}
                  checked={expirationType === EXPIRATION_TYPE.RELATIVE}
                  onChange={handleDurationTypeChange}
                />
                <div>Relative</div>
              </div>

              <div className={styles.radioInput}>
                <Radio
                  name="durationType"
                  value={EXPIRATION_TYPE.ABSOLUTE}
                  checked={expirationType === EXPIRATION_TYPE.ABSOLUTE}
                  onChange={handleDurationTypeChange}
                />
                <div>Absolute</div>
              </div>

              <div className={styles.radioInput}>
                <Radio
                  name="durationType"
                  value={EXPIRATION_TYPE.NEVER}
                  checked={expirationType === EXPIRATION_TYPE.NEVER}
                  onChange={handleDurationTypeChange}
                />
                <div>Never</div>
              </div>
            </div>
            <LineBreak size="small" />
            <Divider />
            <LineBreak size="small" />
            {expirationType === EXPIRATION_TYPE.RELATIVE && (
              <div className={styles.relative}>
                <Input
                  type="number"
                  value={relativeValue}
                  onChange={e => {
                    setRelativeValue(e.target.value);
                    setExpirationFromRelativeate(e.target.value, relativeUnit);
                  }}
                  fullWidth
                />
                <LineBreak size="small" />
                <Select
                  value={relativeUnit}
                  onChange={value => {
                    setRelativeUnit(value);
                    setExpirationFromRelativeate(relativeValue, value);
                  }}
                  name="time"
                >
                  <SelectOption value="hours">Hours</SelectOption>
                  <SelectOption value="days">Days</SelectOption>
                  <SelectOption value="weeks">Weeks</SelectOption>
                  <SelectOption value="months">Months</SelectOption>
                </Select>
              </div>
            )}
            {expirationType === EXPIRATION_TYPE.ABSOLUTE && (
              <div className={styles.absolute}>
                <DatePicker
                  placeholder="YYYY/MM/DD"
                  value={dateValue}
                  onChange={({ detail: { value } }) => {
                    setDateValue(value);
                    setExpirationFromAbsoluteDate(value, timeValue);
                  }}
                  ariaLabelledby="duration-date-label"
                  previousMonthAriaLabel="Previous month"
                  nextMonthAriaLabel="Next month"
                  todayAriaLabel="Today"
                />
                <LineBreak size="small" />
                <TimeInput
                  ariaLabelledby="duration-time-label"
                  use24Hour={true}
                  placeholder="hh:mm:ss"
                  value={timeValue}
                  onChange={({ detail: { value } }) => {
                    setTimeValue(value);
                    setExpirationFromAbsoluteDate(dateValue, value);
                  }}
                />
              </div>
            )}
            {expirationType === EXPIRATION_TYPE.NEVER && (
              <div className={styles.subText}>
                Warning: The request changes will never expire (they will need
                to be removed manually after use)
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

//   return (
//     <Segment isLoading={isLoading}>
//       <div className={styles.container}>
//         <h3>What Permissions would you like?</h3>
//         <LineBreak size="small" />
//         <Tabs
//           activeTabId={activeTab}
//           onChange={e => {
//             setActiveTab(e.detail.activeTabId);
//           }}
//           tabs={[
//             {
//               label: 'Suggestions',
//               id: 'suggested',
//               content: (
//                 <div className={styles.cardContainer}>
//                   {SUGGESTED_CHANGES.map(changeType => (
//                     <Card
//                       variant="outlined"
//                       color="secondary"
//                       className={`${styles.card}`}
//                       contentClassName={styles.cardContent}
//                       key={changeType.header}
//                       clickable
//                     >
//                       <h4>{changeType.header}</h4>
//                       <p>{changeType.subtext}</p>
//                     </Card>
//                   ))}
//                 </div>
//               )
//             },
//             {
//               label: 'Custom',
//               id: 'custom',
//               content: (
//                 <div className={styles.content}>
//                   <LineBreak size="large" />
//                   <div className={styles.content}>
//                     <Block disableLabelPadding label="Change Type" />
//                     <CloudScapeSelect
//                       selectedOption={
//                         selectedChangeType && {
//                           label: selectedChangeType.name,
//                           value: selectedChangeType.id,
//                           description: selectedChangeType.description
//                         }
//                       }
//                       onChange={({ detail }) =>
//                         handleSelectChange(detail.selectedOption)
//                       }
//                       options={options}
//                       filteringType="auto"
//                       selectedAriaLabel="Selected"
//                       placeholder="Select change type"
//                     />
//                     <LineBreak size="large" />
//                     {selectedChangeType && (
//                       <RequestChangeDetails
//                         selectedChangeType={selectedChangeType}
//                         providerDefinition={providerDefinition?.data || []}
//                       />
//                     )}
//                     {tableRows.length > 0 && (
//                       <>
//                         <LineBreak size="large" />
//                         <h4>Selected Changes</h4>
//                         <LineBreak size="small" />
//                         <Table
//                           data={tableRows}
//                           columns={changesColumns}
//                           noResultsComponent={
//                             <div className={styles.subText}>
//                               Please add changes to the request
//                             </div>
//                           }
//                           border="row"
//                         />
//                       </>
//                     )}
//                   </div>
//                   {tableRows.length > 0 && (
//                     <>
//                       <LineBreak size="large" />
//                       <Block disableLabelPadding label="Expiration" />
//                       <div className={styles.radioGroup}>
//                         <div className={styles.radioInput}>
//                           <Radio
//                             name="durationType"
//                             value={EXPIRATION_TYPE.RELATIVE}
//                             checked={
//                               expirationType === EXPIRATION_TYPE.RELATIVE
//                             }
//                             onChange={handleDurationTypeChange}
//                           />
//                           <div>Relative</div>
//                         </div>

//                         <div className={styles.radioInput}>
//                           <Radio
//                             name="durationType"
//                             value={EXPIRATION_TYPE.ABSOLUTE}
//                             checked={
//                               expirationType === EXPIRATION_TYPE.ABSOLUTE
//                             }
//                             onChange={handleDurationTypeChange}
//                           />
//                           <div>Absolute</div>
//                         </div>

//                         <div className={styles.radioInput}>
//                           <Radio
//                             name="durationType"
//                             value={EXPIRATION_TYPE.NEVER}
//                             checked={expirationType === EXPIRATION_TYPE.NEVER}
//                             onChange={handleDurationTypeChange}
//                           />
//                           <div>Never</div>
//                         </div>
//                       </div>
//                       <LineBreak size="small" />
//                       <Divider />
//                       <LineBreak size="small" />
//                       {expirationType === EXPIRATION_TYPE.RELATIVE && (
//                         <div className={styles.relative}>
//                           <Input
//                             type="number"
//                             value={relativeValue}
//                             onChange={e => {
//                               setRelativeValue(e.target.value);
//                               setExpirationFromRelativeate(
//                                 e.target.value,
//                                 relativeUnit
//                               );
//                             }}
//                             fullWidth
//                           />
//                           <LineBreak size="small" />
//                           <Select
//                             value={relativeUnit}
//                             onChange={value => {
//                               setRelativeUnit(value);
//                               setExpirationFromRelativeate(
//                                 relativeValue,
//                                 value
//                               );
//                             }}
//                             name="time"
//                           >
//                             <SelectOption value="hours">Hours</SelectOption>
//                             <SelectOption value="days">Days</SelectOption>
//                             <SelectOption value="weeks">Weeks</SelectOption>
//                             <SelectOption value="months">Months</SelectOption>
//                           </Select>
//                         </div>
//                       )}
//                       {expirationType === EXPIRATION_TYPE.ABSOLUTE && (
//                         <div className={styles.absolute}>
//                           <DatePicker
//                             placeholder="YYYY/MM/DD"
//                             value={dateValue}
//                             onChange={({ detail: { value } }) => {
//                               setDateValue(value);
//                               setExpirationFromAbsoluteDate(value, timeValue);
//                             }}
//                             ariaLabelledby="duration-date-label"
//                             previousMonthAriaLabel="Previous month"
//                             nextMonthAriaLabel="Next month"
//                             todayAriaLabel="Today"
//                           />
//                           <LineBreak size="small" />
//                           <TimeInput
//                             ariaLabelledby="duration-time-label"
//                             use24Hour={true}
//                             placeholder="hh:mm:ss"
//                             value={timeValue}
//                             onChange={({ detail: { value } }) => {
//                               setTimeValue(value);
//                               setExpirationFromAbsoluteDate(dateValue, value);
//                             }}
//                           />
//                         </div>
//                       )}
//                       {expirationType === EXPIRATION_TYPE.NEVER && (
//                         <div className={styles.subText}>
//                           Warning: The request changes will never expire (they
//                           will need to be removed manually after use)
//                         </div>
//                       )}
//                       <LineBreak size="large" />
//                       <Block disableLabelPadding label="Justification" />
//                       <TextArea
//                         fullWidth
//                         value={selfServiceRequest.justification}
//                         onChange={e => setJustification(e.target.value)}
//                       />
//                     </>
//                   )}
//                 </div>
//               )
//             }
//           ]}
//         />
//       </div>
//     </Segment>
//   );
// };

export default SelectChangeType;
