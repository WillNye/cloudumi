import { useCallback, useContext, useMemo } from 'react';
import { DateTime } from 'luxon';
import SelfServiceContext from '../../../SelfServiceContext';
import { Button } from 'shared/elements/Button';
import { LineBreak } from 'shared/elements/LineBreak';
import { Table } from 'shared/elements/Table';
import { EXPIRATION_TYPE } from '../../../constants';
import { Divider } from 'shared/elements/Divider';
import { Select, SelectOption } from 'shared/form/Select';
import { Block } from 'shared/layout/Block';
import { TextArea } from 'shared/form/TextArea';
import { Radio } from 'shared/form/Radio';
import { DatePicker, TimeInput } from '@noqdev/cloudscape';
import { Input } from 'shared/form/Input';
import styles from './RequestExpiration.module.css';

const RequestExpiration = () => {
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

  const tableRows = useMemo(
    () => selfServiceRequest.requestedChanges,
    [selfServiceRequest]
  );

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

  const changesColumns = useMemo(
    () => [
      {
        header: 'Change Name',
        accessorKey: 'name'
      },
      {
        header: 'Description',
        accessorKey: 'description'
      },
      {
        header: 'Actions',
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
    <>
      <div>
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
              Warning: The request changes will never expire (they will need to
              be removed manually after use)
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
    </>
  );
};

export default RequestExpiration;
