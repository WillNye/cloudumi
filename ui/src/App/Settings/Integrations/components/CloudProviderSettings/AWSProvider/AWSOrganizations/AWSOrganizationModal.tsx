import { AxiosError } from 'axios';
import { getSpokeAccounts, updateAWSOrganization } from 'core/API/awsConfig';
import { extractErrorMessage } from 'core/API/utils';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Button } from 'shared/elements/Button';
import { Checkbox } from 'shared/form/Checkbox';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { Segment } from 'shared/layout/Segment';
import { SpokeAccount } from '../SpokeAccounts/types';
import { Select, SelectOption } from 'shared/form/Select';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { LineBreak } from 'shared/elements/LineBreak';
import { useQuery } from '@tanstack/react-query';
import styles from '../AWSProvider.module.css';

const formatSpokeAccount = data => {
  if (data?.account_id) {
    return `${data.account_name || ''} - ${data.account_id}`;
  }
  return '';
};

export const SelectAccount = ({
  label,
  options = [],
  onOptionsLoad,
  onChange,
  value
}) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [spokeAccounts, setSpokeAccounts] = useState<SpokeAccount[]>([]);

  const { isLoading } = useQuery({
    queryFn: getSpokeAccounts,
    queryKey: ['getSpokeAccounts'],
    onSuccess: response => {
      const resData = response?.data;
      setSpokeAccounts(resData);
      onOptionsLoad?.();
    },
    onError: (err: AxiosError) => {
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while getting spoke accounts'
      );
    }
  });

  const handleOptions = (data: SpokeAccount[]) => {
    if (data) {
      return data.map(account => formatSpokeAccount(account));
    }
    return options;
  };

  return (
    <div>
      <Block disableLabelPadding required>
        {label}
      </Block>
      <Select
        name="account_name"
        disabled={isLoading || !spokeAccounts.length}
        onChange={onChange}
        value={value}
      >
        {!spokeAccounts.length && (
          <SelectOption value="">
            You need at least one Spoke Account to proceed.
          </SelectOption>
        )}
        {!isLoading && (
          <SelectOption value="">Select provider type</SelectOption>
        )}
        {!isLoading ? (
          handleOptions(spokeAccounts).map((account, index) => (
            <SelectOption key={index} value={account}>
              {account}
            </SelectOption>
          ))
        ) : (
          <SelectOption value="">Loading accounts...</SelectOption>
        )}
      </Select>
    </div>
  );
};

export const AWSOrganizationModal = ({ defaultValues }) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [accountName, setAccountName] = useState(
    formatSpokeAccount(defaultValues)
  );

  const { register, handleSubmit, watch, setValue } = useForm({
    defaultValues
  });

  const fields = watch();

  const isReady = useMemo(() => {
    return Boolean(fields.org_id && fields.owner && accountName);
  }, [fields, accountName]);

  const onSubmit = useCallback(
    async data => {
      if (!accountName) {
        return;
      }

      const name = accountName.split(' - ');
      data.account_name = name[0];
      data.account_id = name[1];

      setErrorMessage(null);
      setIsLoading(true);
      try {
        await updateAWSOrganization(data);
        setIsLoading(false);
        setSuccessMessage('Successfully updated AWS Organization');
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(
          errorMsg || 'An error occurred while adding hub account'
        );
        setIsLoading(false);
      }
    },
    [accountName]
  );

  const onOptionsLoad = useCallback(() => {
    if (defaultValues?.account_name) {
      setValue('account_name', defaultValues.account_name);
      setValue('ord_id', defaultValues.org_id);
    }
  }, [defaultValues, setValue]);

  return (
    <Segment className={styles.modals}>
      {errorMessage && (
        <Notification
          type={NotificationType.ERROR}
          header={errorMessage}
          showCloseIcon={false}
          fullWidth
        />
      )}
      {successMessage && (
        <Notification
          type={NotificationType.SUCCESS}
          header={successMessage}
          showCloseIcon={false}
          fullWidth
        />
      )}
      <LineBreak />
      <form onSubmit={handleSubmit(onSubmit)}>
        <div>
          <Block disableLabelPadding>Organization Id</Block>
          <Input {...register('org_id', { required: true })} />
        </div>
        <LineBreak />
        <SelectAccount
          label="Spoke Account Name and Id"
          onOptionsLoad={onOptionsLoad}
          onChange={value => {
            setAccountName(value);
          }}
          value={accountName}
        />
        <LineBreak />
        <div>
          <Block disableLabelPadding>Owner</Block>
          <Input {...register('owner', { required: true })} />
        </div>
        <LineBreak />
        <div className={styles.customCheckbox}>
          <Checkbox
            {...register('automatically_onboard_accounts', { required: false })}
          />
          <Block className="form-label">Automatically Onboard Accounts</Block>
        </div>

        <div className={styles.customCheckbox}>
          <Checkbox {...register('sync_account_names', { required: false })} />
          <Block disableLabelPadding>Sync Account Names</Block>
        </div>

        <Button type="submit" disabled={!isReady || isLoading}>
          {isLoading ? 'Loading...' : 'Submit'}
        </Button>
      </form>
    </Segment>
  );
};
