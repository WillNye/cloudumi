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
import styles from '../AWSProvider.module.css';

export const SelectAccount = ({
  register,
  label,
  options = [],
  onOptionsLoad
}) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [spokeAccounts, setSpokeAccounts] = useState<SpokeAccount[]>([]);

  useEffect(() => {
    getAllSpokeAccounts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getAllSpokeAccounts = useCallback(async () => {
    setErrorMessage(null);
    setIsLoading(true);
    try {
      const res = await getSpokeAccounts();
      const resData = res?.data?.data;
      setSpokeAccounts(resData);
      setIsLoading(false);
      onOptionsLoad && onOptionsLoad();
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while getting spoke accounts'
      );
      setIsLoading(false);
    }
  }, [onOptionsLoad]);

  const handleOptions = (data: SpokeAccount[]) => {
    if (data) {
      return data.map(i => `${i.account_name || ''} - ${i.account_id}`);
    }
    return options;
  };

  return (
    <div>
      <Block disableLabelPadding required>
        {label}
      </Block>
      <Select {...register} disabled={isLoading || !spokeAccounts.length}>
        {!spokeAccounts.length && (
          <SelectOption value="">
            You need at least one Spoke Account to proceed.
          </SelectOption>
        )}
        {!isLoading && (
          <SelectOption value="">Select provider type</SelectOption>
        )}
        {!isLoading ? (
          handleOptions(spokeAccounts).map((value, index) => (
            <SelectOption key={index} value={value}>
              {value}
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

  const { register, handleSubmit, watch, setValue } = useForm({
    defaultValues
  });

  const fields = watch();

  const isReady = useMemo(() => {
    return Boolean(fields.org_id && fields.account_name && fields.owner);
  }, [fields]);

  const onSubmit = useCallback(async data => {
    const name = data.account_name.split(' - ');
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
      setErrorMessage(errorMsg || 'An error occurred while adding hub account');
      setIsLoading(false);
    }
  }, []);

  const onOptionsLoad = useCallback(() => {
    if (defaultValues.account_name) {
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
      <br />
      <form onSubmit={handleSubmit(onSubmit)}>
        <div>
          <Block disableLabelPadding>Organization Id</Block>
          <Input {...register('org_id', { required: true })} />
        </div>
        <br />
        <SelectAccount
          label="Spoke Account Name and Id"
          register={{ ...register('account_name', { required: true }) }}
          onOptionsLoad={onOptionsLoad}
        />
        <br />
        <div>
          <Block disableLabelPadding>Owner</Block>
          <Input {...register('owner', { required: true })} />
        </div>
        <br />
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
