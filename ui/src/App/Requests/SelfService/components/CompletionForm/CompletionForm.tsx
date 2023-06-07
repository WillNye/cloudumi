import { LineBreak } from 'shared/elements/LineBreak';
import { CodeEditor } from 'shared/form/CodeEditor';
import { TextArea } from 'shared/form/TextArea';
import { Block } from 'shared/layout/Block';
import { Radio } from 'shared/form/Radio';
import { Divider } from 'shared/elements/Divider';
import { Button } from 'shared/elements/Button';
import { DatePicker, TimeInput } from '@noqdev/cloudscape';
import { useCallback, useContext, useState } from 'react';
import { Input } from 'shared/form/Input';
import { Select, SelectOption } from 'shared/form/Select';
import styles from './CompletionForm.module.css';
import SelfServiceContext from '../../SelfServiceContext';

const CompletionForm = () => {
  const [durationType, setDurationType] = useState('relative');
  const [durationValue, setDurationValue] = useState('');
  const [relativeValue, setRelativeValue] = useState('4');
  const [relativeUnit, setRelativeUnit] = useState('Hours');
  const [absoluteValue, setAbsoluteValue] = useState(new Date());
  const [dateValue, setDateValue] = useState('');
  const [timeValue, setTimeValue] = useState('');

  const {
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

  const handleDurationTypeChange = useCallback(e => {
    setDurationType(e.target.value);
    if (e.target.value === 'never') {
      setDurationValue('');
    }
  }, []);

  return (
    <div className={styles.container}>
      <h3>Request Summary</h3>
      <LineBreak />
      <p className={styles.subText}>
        What is the reason you are requesting this change?
      </p>
      <LineBreak size="large" />

      <div className={styles.section}>
        <div className={styles.content}>
          {/* <h4>Summary</h4> */}
          <LineBreak />
          <div>Provider</div>
          <p className={styles.text}>AWS</p>

          <div>Request Type</div>
          <p className={styles.text}>Request AWS Role Permissions</p>

          <div>Change Type</div>
          <p className={styles.text}>Add s3 Permissions </p>
          <LineBreak size="large" />
          <Block disableLabelPadding label="Justification" />
          <TextArea fullWidth />
          <LineBreak size="large" />
          <Block disableLabelPadding label="Expiration" />
          <div className={styles.radioGroup}>
            <div className={styles.radioInput}>
              <Radio
                name="durationType"
                value="relative"
                checked={durationType === 'relative'}
                onChange={handleDurationTypeChange}
              />
              <div>Relative</div>
            </div>

            <div className={styles.radioInput}>
              <Radio
                name="durationType"
                value="absolute"
                checked={durationType === 'absolute'}
                onChange={handleDurationTypeChange}
              />
              <div>Absolute</div>
            </div>

            <div className={styles.radioInput}>
              <Radio
                name="durationType"
                value="never"
                checked={durationType === 'never'}
                onChange={handleDurationTypeChange}
              />
              <div>Never</div>
            </div>
          </div>
          <LineBreak size="small" />
          <Divider />
          <LineBreak size="small" />
          {durationType === 'relative' && (
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
          {durationType === 'absolute' && (
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
              <LineBreak />
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
          <Button fullWidth>Submit Request</Button>
        </div>
        <div className={styles.codeEditor}>
          <h4>Preview</h4>
          <LineBreak />
          <CodeEditor
            language="json"
            minHeight={650}
            value={JSON.stringify(selfServiceRequest)}
          />
        </div>
      </div>
    </div>
  );
};

export default CompletionForm;
