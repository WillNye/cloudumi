import { Dispatch, FC, useCallback, useState } from 'react';
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
}

const SlackIntegrationModal: FC<SlackIntegrationModalProps> = ({
  isSlackConnected,
  showDialog,
  setShowDialog,
  setIsSlackConnected
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleOnDelete = useCallback(async () => {
    setIsLoading(true);
    try {
      await deleteNoqSlackApp();
      toast.success(`Successfully remove slack App`);
      setIsLoading(false);
      setIsSlackConnected(false);
      setShowDialog(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      toast.error(errorMsg || `Error when removing slack App`);
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
      <Segment>
        <div>
          Our Slack app offers real-time notifications, seamless collaboration,
          and customizable settings to help you work more efficiently with your
          team. With the app, you&apos;ll stay informed and engaged, and be able
          to work on projects and tasks directly from Slack. Install
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
