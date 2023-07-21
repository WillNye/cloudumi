import { Dispatch, FC, useCallback, useEffect, useState } from 'react';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import { deleteNoqGithubApp, addNoqGithubApp } from 'core/API/integrations';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Segment } from 'shared/layout/Segment';
import { toast } from 'react-toastify';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Block } from 'shared/layout/Block';
import { Checkbox } from 'shared/form/Checkbox';
import { ChangeEvent } from 'react';
import { LineBreak } from 'shared/elements/LineBreak';
import { Select, SelectOption } from 'shared/form/Select';
import { CodeBlock } from 'shared/elements/CodeBlock';
import axios from 'core/Axios/Axios';
import styles from './GithubIntegrationModal.module.css';

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
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [mergeOnApproval, setMergeOnApproval] = useState(false);
  const [integrationConfig, setIntegrationConfig] = useState(null);

  useEffect(() => {
    axios
      .get('/api/v3/github/repos/')
      .then(response => {
        setRepos(response.data.data.repos);
        setSelectedRepo(response.data.data.configured_repo || null);
        setMergeOnApproval(response.data.data.merge_on_approval || false);
        setIntegrationConfig(response.data.data.integration_config || null);
      })
      .catch(error => {
        console.error(error);
      });
  }, [isGithubConnected]);

  const handleRepoChange = repo => {
    setSelectedRepo(repo);
    axios.post('/api/v3/github/repos/', {
      repo_name: repo,
      merge_on_approval: mergeOnApproval
    });
  };

  const handleAutoApplyChange = (e: ChangeEvent<HTMLInputElement>) => {
    setMergeOnApproval(e.target.checked);
    axios.post('/api/v3/github/repos/', {
      repo_name: selectedRepo,
      merge_on_approval: e.target.checked
    });
  };

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
    const confirmDeletion = window.confirm(
      'Please note that you will also need to go to your GitHub Organization Settings ' +
        'to manually to uninstall the app.\n\n' +
        'Do you want to proceed with removing the GitHub integration?'
    );
    if (confirmDeletion) {
      setIsLoading(true);
      try {
        await deleteMutation();
        toast.success(`Successfully removed Github App`);
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
      toast.error(errorMsg || `Error when generating Github installation Link`);
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
        {!isGithubConnected && (
          <>
            <div>
              Noq&apos;s Github App integrates with your IAMbic repository.
            </div>
            <LineBreak size="large" />
            <div>
              You will need GitHub App installation privilege to complete the
              installation.
            </div>
            <div>
              If you are not Github Administrator, installation will require
              multiple pass and your GitHub administrator&apos;s approval.
            </div>
            <LineBreak size="large" />
            <div>
              When GitHub prompts you for repository selection, please select
              only your organization&apos;s iambic-templates repository. This
              will appropriately restrict the permissions of the Noq GitHub App.
            </div>
            <LineBreak size="large" />
          </>
        )}

        {isGithubConnected && (
          <>
            <div>
              To allow Noq Platform to approve the IAMbic PR, add following
              integration to your IAMbic config.
            </div>
            <LineBreak size="large" />
            <div className={styles.codeBlockContainer}>
              <CodeBlock code={integrationConfig} />
            </div>
            <LineBreak size="large" />
          </>
        )}

        {isGithubConnected && (
          <>
            <Block label="Select Repository" disableLabelPadding />
            <Select
              id="repo"
              name={selectedRepo}
              value={selectedRepo}
              onChange={handleRepoChange}
            >
              {repos.map(repo => (
                <SelectOption key={repo} value={repo}>
                  {repo}
                </SelectOption>
              ))}
            </Select>
            <LineBreak size="large" />
            <div className={styles.customCheckbox}>
              <Checkbox
                {...{
                  checked: mergeOnApproval,
                  onChange: handleAutoApplyChange
                }}
              />
              <Block className="form-label">
                Auto-apply IAMbic changes after they are approved
              </Block>
            </div>
            <LineBreak size="large" />
          </>
        )}

        {isGithubConnected ? (
          <Button
            color="error"
            onClick={handleOnDelete}
            fullWidth
            disabled={isLoading}
          >
            {isLoading ? 'Removing...' : 'Remove GitHub Integration'}
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
