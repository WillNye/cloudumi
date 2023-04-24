import { Dispatch, FC, useCallback, useEffect, useState } from 'react';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import { deleteNoqSlackApp, addNoqSlackApp } from 'core/API/integrations';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Segment } from 'shared/layout/Segment';
import { toast } from 'react-toastify';

interface SlackIntegrationModalProps {
  showDialog: boolean;
  setShowDialog: Dispatch<boolean>;
  isSlackConnected: boolean;
  setIsSlackConnected: Dispatch<boolean>;
  checkStatus: () => void;
  isGettingIntegrations: boolean;
}

const SlackIntegrationModal: FC<SlackIntegrationModalProps> = ({
  isSlackConnected,
  showDialog,
  setShowDialog,
  setIsSlackConnected,
  checkStatus,
  isGettingIntegrations
}) => {
  const [isLoading, setIsLoading] = useState(false);

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
      await deleteNoqSlackApp();
      toast.success(`Successfully remove Slack App`);
      setIsLoading(false);
      setIsSlackConnected(false);
      setShowDialog(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      toast.error(errorMsg || `Error when removing Slack App`);
      setIsLoading(false);
    }
  }, [setIsSlackConnected, setShowDialog]);

  const handleOnGenerateLink = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await addNoqSlackApp();
      const data = res.data;
      window.open(data.data.slack_install_url, '_blank');
      setIsLoading(false);
      setShowDialog(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      toast.error(errorMsg || `Error when generating Slack intsallation Link`);
      setIsLoading(false);
    }
  }, [setShowDialog]);

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
        <br />
        <br />
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
