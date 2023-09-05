import { Dispatch, FC, useCallback, useEffect, useState } from 'react';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import {
  deleteNoqGithubApp,
  addNoqGithubApp,
  getGithubRepos
} from 'core/API/integrations';
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
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [mergeOnApproval, setMergeOnApproval] = useState(false);
  const [integrationConfig, setIntegrationConfig] = useState(null);
  const [isUpdatingGithubConfig, setIsUpdatingGithubConfig] = useState(false);

  const handleRepoChange = repo => {
    setSelectedRepo(repo);
  };

  const handleAutoApplyChange = (e: ChangeEvent<HTMLInputElement>) => {
    setMergeOnApproval(e.target.checked);
  };

  const handleonUpdate = useCallback(
    async e => {
      e.preventDefault();
      setIsUpdatingGithubConfig(true);
      try {
        await axios.post('/api/v3/github/repos/', {
          repo_name: selectedRepo,
          merge_on_approval: mergeOnApproval
        });
        setIsUpdatingGithubConfig(false);
        toast.success(`Successfully updated Github config`);
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        toast.error(errorMsg || `Error when updating Github config`);
        setIsUpdatingGithubConfig(false);
      }
    },
    [selectedRepo, mergeOnApproval]
  );

  const { mutateAsync: deleteMutation, isLoading: isDeleting } = useMutation({
    mutationFn: deleteNoqGithubApp
  });

  const { refetch, isFetching: isGeneratingLink } = useQuery({
    queryFn: addNoqGithubApp,
    queryKey: ['installGithubLink'],
    onSuccess: data => {
      window.open(data.data.github_install_url, '_blank');
    },
    enabled: false
  });

  const { isLoading } = useQuery({
    queryFn: getGithubRepos,
    queryKey: ['getGithubRepos'],
    onSuccess: ({ data }) => {
      setRepos(data.repos);
      setSelectedRepo(data.configured_repo || null);
      setMergeOnApproval(data.merge_on_approval || false);
      setIntegrationConfig(data.integration_config || null);
    }
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
    setIsDeleteModalOpen(false);
    try {
      await deleteMutation();
      toast.success(`Successfully removed Github App`);
      setShowDialog(false);
      checkStatus();
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      toast.error(errorMsg || `Error when removing Github App`);
    }
  }, [setShowDialog, deleteMutation, checkStatus]);

  const handleOnGenerateLink = useCallback(async () => {
    try {
      await refetch();
      setShowDialog(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      toast.error(errorMsg || `Error when generating Github installation Link`);
    }
  }, [setShowDialog, refetch]);

  return (
    <>
      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        header={'Github Integration'}
        disablePadding
        size="medium"
        showCloseIcon
      >
        <Segment
          isLoading={
            isGettingIntegrations ||
            isLoading ||
            isGeneratingLink ||
            isUpdatingGithubConfig
          }
        >
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
                will appropriately restrict the permissions of the Noq GitHub
                App.
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
              <form onSubmit={handleonUpdate}>
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
                <LineBreak />
                <Button
                  size="small"
                  type="submit"
                  fullWidth
                  disabled={isLoading || isDeleting}
                >
                  {isUpdatingGithubConfig
                    ? 'updating...'
                    : 'Update Configuration'}
                </Button>
                <LineBreak />
              </form>
            </>
          )}

          {isGithubConnected ? (
            <Button
              color="error"
              onClick={() => setIsDeleteModalOpen(true)}
              fullWidth
              disabled={isLoading || isDeleting}
              size="small"
            >
              {isDeleting ? 'Removing...' : 'Remove Integration'}
            </Button>
          ) : (
            <Button
              onClick={handleOnGenerateLink}
              color="secondary"
              fullWidth
              disabled={isLoading}
              size="small"
            >
              {isLoading ? 'Generating...' : 'Install'}
            </Button>
          )}
        </Segment>
      </Dialog>
      <Dialog
        showDialog={isDeleteModalOpen}
        setShowDialog={setIsDeleteModalOpen}
        header="Delete GitHub Connection?"
      >
        <div className={styles.confirmationModal}>
          <p>
            Please note that you will also need to go to your GitHub
            Organization Settings to manually to uninstall the app.
          </p>
          <LineBreak size="small" />
          <p>Do you want to proceed with removing the GitHub integration?</p>
          <LineBreak size="large" />
          <div className={styles.modalActions}>
            <Button
              variant="outline"
              size="small"
              onClick={() => setIsDeleteModalOpen(false)}
            >
              Cancel
            </Button>
            <Button color="error" size="small" onClick={handleOnDelete}>
              Delete
            </Button>
          </div>
        </div>
      </Dialog>
    </>
  );
};

export default GithubIntegrationModal;
