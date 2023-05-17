import { Dispatch, FC, useCallback, useEffect, useState } from 'react';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import { deleteNoqSlackApp, addNoqSlackApp } from 'core/API/integrations';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Segment } from 'shared/layout/Segment';
import { toast } from 'react-toastify';
import { useMutation, useQuery } from '@tanstack/react-query';
import { LineBreak } from 'shared/elements/LineBreak';

interface SlackIntegrationModalProps {
  showDialog: boolean;
  setShowDialog: Dispatch<boolean>;
  isSlackConnected: boolean;
  checkStatus: () => void;
  isGettingIntegrations: boolean;
}

const SlackIntegrationModal: FC<SlackIntegrationModalProps> = ({
  isSlackConnected,
  showDialog,
  setShowDialog,
  checkStatus,
  isGettingIntegrations
}) => {
  const [isLoading, setIsLoading] = useState(false);
  0;
  const { mutateAsync: deleteMutation } = useMutation({
    mutationFn: deleteNoqSlackApp
  });
  const { refetch } = useQuery({
    queryFn: addNoqSlackApp,
    queryKey: ['installSlackLink'],
    onSuccess: data => {
      window.open(data.data.slack_install_url, '_blank');
    },
    enabled: false
  });

  useEffect(
    function onMount() {
      if (showDialog) {
        checkStatus();
      }
    },
    [checkStatus, showDialog]
  );

  const handleOnDelete = useCallback(async () => {
    setIsLoading(true);
    try {
      await deleteMutation();
      toast.success(`Successfully remove Slack App`);
      setIsLoading(false);
      setShowDialog(false);
      checkStatus();
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      toast.error(errorMsg || `Error when removing Slack App`);
      setIsLoading(false);
    }
  }, [setShowDialog, deleteMutation, checkStatus]);

  const handleOnGenerateLink = useCallback(async () => {
    setIsLoading(true);
    try {
      await refetch();
      setIsLoading(false);
      setShowDialog(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      toast.error(errorMsg || `Error when generating Slack intsallation Link`);
      setIsLoading(false);
    }
  }, [setShowDialog, refetch]);

  return (
    <Dialog
      showDialog={showDialog}
      setShowDialog={setShowDialog}
      header={'Slack Integration'}
      disablePadding
      size="medium"
      showCloseIcon
    >
      <Segment isLoading={isGettingIntegrations}>
        <div>
          Noq&apos;s Slack App integration provides self-service workflows,
          real-time notifications, and collaboration to help you work more
          efficiently with your team.
        </div>
        <LineBreak size="large" />
        {isSlackConnected ? (
          <Button
            color="error"
            onClick={handleOnDelete}
            fullWidth
            disabled={isLoading}
          >
            {isLoading ? 'Removing...' : 'Remove'}
          </Button>
        ) : (
          <Button
            onClick={handleOnGenerateLink}
            color="secondary"
            fullWidth
            disabled={isLoading}
          >
            {isLoading ? 'Generating...' : 'Install'}
          </Button>
        )}
      </Segment>
    </Dialog>
  );
};

export default SlackIntegrationModal;
