import { Dispatch, FC, useCallback, useEffect, useState } from 'react';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import { deleteNoqGithubApp, addNoqGithubApp } from 'core/API/integrations';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Segment } from 'shared/layout/Segment';
import { toast } from 'react-toastify';
import { useMutation, useQuery } from '@tanstack/react-query';
import { LineBreak } from 'shared/elements/LineBreak';

interface GithubIntegrationModalProps {
  showDialog: boolean;
  setShowDialog: Dispatch<boolean>;
  isGithubConnected: boolean;
  checkStatus: () => void;
  isGettingIntegrations: boolean;
}

const GithubIntegrationModal: FC<GithubIntegrationModalProps> = ({
  isGithubConnected,
  showDialog,
  setShowDialog,
  checkStatus,
  isGettingIntegrations
}) => {
  const [isLoading, setIsLoading] = useState(false);
  0;
  const { mutateAsync: deleteMutation } = useMutation({
    mutationFn: deleteNoqGithubApp
  });
  const { refetch } = useQuery({
    queryFn: addNoqGithubApp,
    queryKey: ['installGithubLink'],
    onSuccess: data => {
      window.open(data.data.github_install_url, '_blank');
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
      toast.success(`Successfully remove Github App`);
      setIsLoading(false);
      setShowDialog(false);
      checkStatus();
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      toast.error(errorMsg || `Error when removing Github App`);
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
      toast.error(errorMsg || `Error when generating Github intsallation Link`);
      setIsLoading(false);
    }
  }, [setShowDialog, refetch]);

  return (
    <Dialog
      showDialog={showDialog}
      setShowDialog={setShowDialog}
      header={'Github Integration'}
      disablePadding
      size="medium"
      showCloseIcon
    >
      <Segment isLoading={isGettingIntegrations}>
        <div>Noq&apos;s Github App integrates with your IAMbic repository.</div>
        <LineBreak size="large" />
        {isGithubConnected ? (
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

export default GithubIntegrationModal;
