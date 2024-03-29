import { AxiosError } from 'axios';
import { updateSpokeAccount } from 'core/API/awsConfig';
import { extractErrorMessage } from 'core/API/utils';
import { useCallback, useMemo, useState } from 'react';

import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { Button } from 'shared/elements/Button';
import { Icon } from 'shared/elements/Icon';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { Segment } from 'shared/layout/Segment';
import { removeUserAccount } from './utils';
import { Checkbox } from 'shared/form/Checkbox';
import { Notification, NotificationType } from 'shared/elements/Notification';
import styles from '../AWSProvider.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { Chip } from 'shared/elements/Chip';

const SpokeAccountUsers = ({ category, setValue, labels }) => (
  <div>
    {labels.map((selectedValue, index) => {
      return (
        <Chip key={index}>
          {selectedValue}
          <Icon
            name="delete"
            onClick={() => {
              const newValues = removeUserAccount(labels, selectedValue);
              setValue(category, newValues);
            }}
          />
        </Chip>
      );
    })}
  </div>
);

export const SpokeAccountModal = ({ defaultValues, aws }) => {
  const [accountOwner, setAccountOwner] = useState('');
  const [accountViewer, setAccountViewer] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { register, handleSubmit, watch, setValue } = useForm({
    defaultValues
  });

  const fields = watch();

  const navigate = useNavigate();

  const isReady = useMemo(() => fields.name !== '', [fields]);
  const isIneligible = useMemo(
    () => aws?.data?.spoke_account_role?.status === 'ineligible',
    [aws]
  );

  const onSubmit = useCallback(async data => {
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsLoading(true);
    try {
      await updateSpokeAccount(data);
      setSuccessMessage('Successfully updated spoke account');
      setIsLoading(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while updating spoke account'
      );
      setIsLoading(false);
    }
  }, []);

  const handleClick = useCallback(() => {
    navigate('/settings/integrations/aws/onboarding');
  }, [navigate]);

  if (defaultValues) {
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
            <Block>Account Name</Block>
            <Input {...register('account_name', { required: true })} />
          </div>
          <LineBreak />
          <div className={styles.customCheckbox}>
            <Checkbox {...register('delegate_admin_to_owner')} />
            <Block>Delegate Policy Request Administration to Owner</Block>
          </div>
          <LineBreak />
          <div>
            <Block>Account Owners</Block>
            <Input
              placeholder="Add owners ..."
              value={accountOwner}
              onChange={e => {
                e.preventDefault();
                setAccountOwner(e.target.value);
              }}
              suffix={
                <Button
                  type="button"
                  size="small"
                  color="secondary"
                  onClick={e => {
                    e.preventDefault();
                    if (!accountOwner) {
                      return;
                    }
                    setValue('owners', [
                      ...(fields.owners || []),
                      accountOwner
                    ]);
                    setAccountOwner('');
                  }}
                >
                  Add
                </Button>
              }
            />
            <LineBreak />
            <SpokeAccountUsers
              category="owners"
              labels={fields.owners || []}
              setValue={setValue}
            />
          </div>
          <LineBreak />
          <div className={styles.customCheckbox}>
            <Checkbox {...register('restrict_viewers_of_account_resources')} />
            <Block>Restrict Viewers of Account Resources</Block>
          </div>
          <LineBreak />
          <div>
            <Block disableLabelPadding>Account Viewers</Block>
            <Input
              placeholder="Add viewers ..."
              value={accountViewer}
              onChange={e => {
                e.preventDefault();
                setAccountViewer(e.target.value);
              }}
              suffix={
                <Button
                  type="button"
                  size="small"
                  color="secondary"
                  onClick={e => {
                    e.preventDefault();
                    if (!accountViewer) {
                      return;
                    }
                    setValue('viewers', [
                      ...(fields.viewers || []),
                      accountViewer
                    ]);
                    setAccountViewer('');
                  }}
                >
                  Add
                </Button>
              }
            />
            <LineBreak />
            <SpokeAccountUsers
              category="viewers"
              labels={fields.viewers || []}
              setValue={setValue}
            />
          </div>
          <LineBreak />
          <Button type="submit" disabled={!isReady || isLoading}>
            {isLoading ? 'Loading...' : 'Submit'}
          </Button>
        </form>
      </Segment>
    );
  }

  const ACCOUNT_A = <strong style={{ fontWeight: 'bold' }}>*account_a*</strong>;
  const ACCOUNT_B = <strong style={{ fontWeight: 'bold' }}>*account_b*</strong>;

  return (
    <Segment>
      {isIneligible ? (
        <>
          <p style={{ textAlign: 'center' }}>
            You cannot connect your Spoke Accounts before having a Hub Account
            connected.
            <LineBreak />
            <strong>
              If you already did, please try to refresh the screen.
            </strong>
          </p>
          <p style={{ textAlign: 'center' }}>
            <Button onClick={() => aws.get()}>Refresh Screen</Button>
          </p>
        </>
      ) : (
        <>
          <p style={{ textAlign: 'center', lineHeight: '1.8em' }}>
            Your spoke accounts are all of the AWS accounts that you want to use
            Noq in. <br />
            We will help you create spoke roles on these accounts. Noq will
            access these roles by first assuming your central (&quot;hub&quot;)
            account role and then assuming the spoke role in the target account.
            For example, assume that a customer has configured Noq&apos;s
            central role on {ACCOUNT_A}. They&apos;ve configured spoke roles on{' '}
            {ACCOUNT_A} and {ACCOUNT_B} {''}
            <br />
            (Yes, the central account must also have a spoke role if you want
            Noq to work on it).
            <br />
            If Noq needs to write a policy to an IAM role on {ACCOUNT_B}, it
            will assume the central role on {ACCOUNT_A} with an external ID that
            is unique to your organization, and then it will assume the spoke
            role on {ACCOUNT_B}. It will write the IAM policy from the spoke
            role on {ACCOUNT_B}.
          </p>
          <LineBreak />
          <Button onClick={handleClick} fullWidth>
            Proceed
          </Button>
        </>
      )}
    </Segment>
  );
};
