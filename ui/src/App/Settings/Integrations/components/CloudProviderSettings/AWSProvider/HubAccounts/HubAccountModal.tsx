import {
  Dispatch,
  Ref,
  forwardRef,
  useCallback,
  useMemo,
  useState
} from 'react';
import { useForm } from 'react-hook-form';
import { Segment } from 'shared/layout/Segment';
import { Button } from 'shared/elements/Button';
import { Block } from 'shared/layout/Block';
import { Input } from 'shared/form/Input';
import { updateHubAccount } from 'core/API/awsConfig';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { LineBreak } from 'shared/elements/LineBreak';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { HubAccount } from './types';

interface HubAccountModalprops {
  onClose: () => void;
  defaultValues: HubAccount | null;
  aws: any;
}

export const HubAccountModal = forwardRef(
  (
    { onClose, defaultValues, aws }: HubAccountModalprops,
    ref: Ref<HTMLButtonElement>
  ) => {
    const [isLoading, setIsLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const navigate = useNavigate();

    const { register, handleSubmit, watch } = useForm({ defaultValues });

    const { mutateAsync: updateHubAccountMutation } = useMutation({
      mutationFn: formData => updateHubAccount(formData),
      mutationKey: ['updateHubAccount']
    });

    const fields = watch();

    const isIneligible = useMemo(
      () => aws.data?.central_account_role?.status === 'ineligible',
      [aws]
    );

    const isReady = useMemo(() => fields.name !== '', [fields]);

    const onSubmit = useCallback(
      async data => {
        setErrorMessage(null);
        setSuccessMessage(null);
        setIsLoading(true);
        try {
          await updateHubAccountMutation(data);
          setSuccessMessage('Successfully updated hub account');
          setIsLoading(false);
        } catch (error) {
          const err = error as AxiosError;
          const errorRes = err?.response;
          const errorMsg = extractErrorMessage(errorRes?.data);
          setErrorMessage(
            errorMsg || 'An error occurred while updating hub account'
          );
          setIsLoading(false);
        }
      },
      [updateHubAccountMutation]
    );

    const handleClick = useCallback(() => {
      onClose();
      navigate('/settings/integrations/aws/onboarding');
    }, [navigate, onClose]);

    if (defaultValues) {
      return (
        <Segment>
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
              <Block disableLabelPadding>Role Name</Block>
              <Input {...register('name', { required: true })} />
            </div>
            <LineBreak />
            <Button type="submit" disabled={!isReady || isLoading}>
              Submit
            </Button>
          </form>
        </Segment>
      );
    }

    return (
      <Segment>
        {isIneligible ? (
          <p style={{ textAlign: 'center', lineHeight: '1.5rem' }}>
            Ineligible. You are unable to connect your account, please ask to
            your admin to help.
          </p>
        ) : (
          <>
            <p style={{ textAlign: 'left', lineHeight: '1.5rem' }}>
              Your hub role is Noq&apos;s entrypoint into your environment.
              Whenever Noq attempts to gather information about your resources,
              update your resources, or broker credentials to your roles, it
              will first access your hub account with an external ID that is
              unique to your organization. Your hub account is an AWS account of
              your choosing that will be the entrypoint for Noq into your
              environment. Our onboarding process will walk you through the
              process of creating this role.
            </p>
            <ol>
              <li>
                Authenticate to the AWS account that you want to use as the Hub
                Account.
              </li>
              <li>
                Start the process by clicking the Execute CloudFormation
                button.&nbsp; This will open up a Cloudformation stack in a new
                tab.
              </li>
              <li>
                Execute the Cloudformation, and revisit this page after it has
                successfully executed.
              </li>
            </ol>
            <LineBreak />
            <Button ref={ref} onClick={handleClick} fullWidth>
              Proceed
            </Button>
          </>
        )}
      </Segment>
    );
  }
);
