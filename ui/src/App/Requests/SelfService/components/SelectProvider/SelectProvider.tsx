import { useState, useEffect } from 'react';

import { Segment } from 'shared/layout/Segment';
import RequestCard from '../RequestCard';
import awsIcon from '../../../../../assets/integrations/awsIcon.svg';
import gsuiteIcon from '../../../../../assets/integrations/gsuiteIcon.svg';
import azureADIcon from '../../../../../assets/integrations/azureADIcon.svg';
import oktaIcon from '../../../../../assets/integrations/oktaIcon.svg';
import { Select, SelectOption } from 'shared/form/Select';
import { Block } from 'shared/layout/Block';
import styles from './SelectProvider.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { Link } from 'react-router-dom';

import { Button } from 'shared/elements/Button';
import { Radio } from 'shared/form/Radio';
import {
  DatePicker,
  PropertyFilter,
  PropertyFilterProps,
  TimeInput
} from '@noqdev/cloudscape';
import { Input } from 'shared/form/Input';

const SelectProvider = () => {
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [selectedAction, setSelectedAction] = useState(null);
  const [selectedMethod, setSelectedMethod] = useState(null);

  const handleProviderSelection = provider => {
    setSelectedProvider(provider);
  };

  const handleActionSelection = action => {
    setSelectedAction(action);
  };

  const handleMethodSelection = method => {
    setSelectedMethod(method);
  };

  if (selectedProvider === 'AWS' && !selectedAction) {
    return (
      <SelectAWSAction
        goBack={() => setSelectedProvider(null)}
        handleActionSelection={handleActionSelection}
      />
    );
  }

  if (
    selectedProvider === 'AWS' &&
    selectedAction === 'Request AWS Credentials or Console Access' &&
    !selectedMethod
  ) {
    return (
      <SelectAWSMethod
        goBack={() => setSelectedAction(null)}
        handleMethodSelection={handleMethodSelection}
      />
    );
  }

  if (
    selectedProvider === 'AWS' &&
    selectedAction === 'Request AWS Credentials or Console Access' &&
    selectedMethod
  ) {
    return (
      <AWSAccessForm
        goBack={() => setSelectedMethod(null)}
        method={selectedMethod}
      />
    );
  }

  return (
    <Segment>
      <div className={styles.container}>
        <h3>Select Provider</h3>
        <LineBreak />
        <p className={styles.subText}>
          Please choose a provider from the list below
        </p>
        <LineBreak size="large" />
        <div className={styles.cardList}>
          <RequestCard
            title="AWS"
            icon={awsIcon}
            description="Amazon web services (AWS)"
            onClick={() => handleProviderSelection('AWS')}
          />

          <RequestCard title="Okta" icon={oktaIcon} description="Okta" />

          <RequestCard
            title="Azure AD"
            icon={azureADIcon}
            description="Azure Active Directory"
          />

          <RequestCard
            title="Google Workspace"
            icon={gsuiteIcon}
            description="Google Workspace"
          />
        </div>
        <LineBreak size="large" />
        <p className={styles.subText}>
          Can&apos;t find what you&apos;re looking for? Have an administrator{' '}
          <Link to="/settings/integrations">click here</Link> to add a new
          provider
        </p>
      </div>
    </Segment>
  );
};

const SelectAWSAction = ({ goBack, handleActionSelection }) => {
  return (
    <Segment>
      <Button color={'secondary'} size="small" onClick={goBack}>
        Back
      </Button>
      <div className={styles.container}>
        <h3>Select AWS Action</h3>
        <LineBreak />
        <p className={styles.subText}>
          Please choose an action from the list below
        </p>
        <LineBreak size="large" />
        <div className={styles.cardList}>
          <RequestCard
            title="Request AWS Credentials or Console Access"
            icon={awsIcon}
            description=""
            onClick={() =>
              handleActionSelection('Request AWS Credentials or Console Access')
            }
          />

          <RequestCard
            title="Request AWS IAM Permissions to a Cloud Resource"
            icon={awsIcon}
            description=""
          />

          <RequestCard
            title="Create a Cloud IAM Resource"
            icon={awsIcon}
            description=""
          />
        </div>
        <LineBreak size="large" />
      </div>
    </Segment>
  );
};

const SelectAWSMethod = ({ goBack, handleMethodSelection }) => {
  return (
    <Segment>
      <div className={styles.buttonContainer}>
        <Button color={'secondary'} size="small" onClick={goBack}>
          Back
        </Button>
      </div>
      <div className={styles.container}>
        <h3>Select Method</h3>
        <LineBreak />
        <p className={styles.subText}>
          Please choose a method from the list below
        </p>
        <LineBreak size="large" />
        <div className={styles.cardList}>
          <RequestCard
            title="Via AWS Identity Center (SSO)"
            icon={awsIcon}
            description=""
            onClick={() =>
              handleMethodSelection('Via AWS Identity Center (SSO)')
            }
          />

          <RequestCard
            title="Via AWS IAM Roles"
            icon={awsIcon}
            description=""
            onClick={() => handleMethodSelection('Via AWS IAM Roles')}
          />
        </div>
        <LineBreak size="large" />
      </div>
    </Segment>
  );
};

const AWSAccessForm = ({ goBack, method }) => {
  const [selectedPermissionSets, setSelectedPermissionSets] = useState([]);
  const [selectedAccounts, setSelectedAccounts] = useState([]);
  const [durationType, setDurationType] = useState('relative');
  const [durationValue, setDurationValue] = useState('');
  const [justification, setJustification] = useState('');
  const [permissionSetOptions, setPermissionSetOptions] = useState([]);
  const [accountOptions, setAccountOptions] = useState([]);

  const handleAccountsChange = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const selectedOptions = Array.from(event.target.selectedOptions);
    setSelectedAccounts(selectedOptions.map(option => option.value));
  };

  const handlePermissionSetsChange = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const selectedOptions = Array.from(event.target.selectedOptions);
    setSelectedPermissionSets(selectedOptions.map(option => option.value));
  };

  useEffect(() => {
    // replace with actual API request
    fetch('/api/v4/templates?resource_id={query}&template_type={template_type}')
      .then(response => response.json())
      .then(data => {
        setPermissionSetOptions(data.permissionSets);
        setAccountOptions(data.accounts);
      });
  }, []);

  const handleFormSubmit = event => {
    event.preventDefault();
    // handle form submission logic here
  };

  return (
    <Segment>
      <Button color={'secondary'} size="small" onClick={goBack}>
        Back
      </Button>
      <form onSubmit={handleFormSubmit} className={styles.form}>
        {method === 'Via AWS Identity Center (SSO)' && (
          <>
            <Block disableLabelPadding>
              Select AWS Identity Center (SSO) Permission Sets
            </Block>
            <Select
              multiple
              value={selectedPermissionSets}
              onChange={handlePermissionSetsChange}
            >
              {permissionSetOptions.map(option => (
                <SelectOption key={option.id} value={option.value}>
                  {option.label}
                </SelectOption>
              ))}
            </Select>
            <Block disableLabelPadding>Select AWS Accounts</Block>
            <Select
              multiple
              value={selectedAccounts}
              onChange={handleAccountsChange}
            >
              {accountOptions.map(option => (
                <SelectOption key={option.id} value={option.value}>
                  {option.label}
                </SelectOption>
              ))}
            </Select>
          </>
        )}
        {method === 'Via AWS IAM Roles' && (
          <Select
            multiple
            value={selectedAccounts}
            onChange={handleAccountsChange}
          >
            {accountOptions.map(option => (
              <SelectOption key={option.id} value={option.value}>
                {option.label}
              </SelectOption>
            ))}
          </Select>
        )}
        <div className={styles.duration}>
          <Duration
            type={durationType}
            value={durationValue}
            setType={setDurationType}
            setValue={setDurationValue}
          />
        </div>
        <textarea
          className={styles.justification}
          value={justification}
          onChange={event => setJustification(event.target.value)}
          placeholder="Justification"
        />
        <br />
        <Button type="submit" className={styles.submit}>
          Submit
        </Button>
      </form>
    </Segment>
  );
};

interface DurationProps {
  type: string;
  value: string;
  setType: React.Dispatch<React.SetStateAction<string>>;
  setValue: React.Dispatch<React.SetStateAction<string>>;
}

const Duration = ({ type, value, setType, setValue }) => {
  const [relativeValue, setRelativeValue] = useState('');
  const [relativeUnit, setRelativeUnit] = useState('Hours');
  const [absoluteValue, setAbsoluteValue] = useState(new Date());
  const [dateValue, setDateValue] = useState('');
  const [timeValue, setTimeValue] = useState('');

  const handleDurationTypeChange = e => {
    setType(e.target.value);
    if (e.target.value === 'never') {
      setValue('');
    }
  };

  const handleRelativeValueChange = e => {
    setRelativeValue(e.target.value);
  };

  const handleRelativeUnitChange = e => {
    setRelativeUnit(e.target.value);
  };

  const handleDateChange = value => {
    setDateValue(value);
  };

  const handleTimeChange = value => {
    setTimeValue(value);
  };

  useEffect(() => {
    if (type === 'relative') {
      setValue(relativeValue + ' ' + relativeUnit);
    } else if (type === 'absolute') {
      setValue(`${dateValue} ${timeValue}`);
    }
  }, [type, relativeValue, relativeUnit, dateValue, timeValue]);

  return (
    <div>
      <Block>When should the access expire?</Block>
      <br />
      <div className={styles.radioGroup}>
        <div className={styles.radioInput}>
          <Radio
            name="durationType"
            value="relative"
            checked={type === 'relative'}
            onChange={handleDurationTypeChange}
          />
          <Block disableLabelPadding>Relative</Block>
        </div>

        <div className={styles.radioInput}>
          <Radio
            name="durationType"
            value="absolute"
            checked={type === 'absolute'}
            onChange={handleDurationTypeChange}
          />
          <Block disableLabelPadding>Absolute</Block>
        </div>

        <div className={styles.radioInput}>
          <Radio
            name="durationType"
            value="never"
            checked={type === 'never'}
            onChange={handleDurationTypeChange}
          />
          <Block disableLabelPadding>Never</Block>
        </div>
      </div>

      {type === 'relative' && (
        <div>
          <div className={styles.relative}>
            <Input
              type="number"
              value={relativeValue}
              onChange={handleRelativeValueChange}
            />
            <Select value={relativeUnit} onChange={handleRelativeUnitChange}>
              <SelectOption value="Hours">Hours</SelectOption>
              <SelectOption value="Days">Days</SelectOption>
              <SelectOption value="Weeks">Weeks</SelectOption>
              <SelectOption value="Months">Months</SelectOption>
            </Select>
          </div>
        </div>
      )}

      {type === 'absolute' && (
        <div className={styles.absolute}>
          <DatePicker
            placeholder="YYYY/MM/DD"
            value={dateValue}
            onChange={({ detail: { value } }) => handleDateChange(value)}
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
            onChange={({ detail: { value } }) => handleTimeChange(value)}
          />
        </div>
      )}
    </div>
  );
};

export default SelectProvider;
