import { Table } from 'shared/elements/Table';
import { HubAccountsColumns } from './constants';
import { deleteHubAccount } from 'core/API/awsConfig';
import { useEffect, useMemo, useRef, useState } from 'react';
import { HubAccount } from './types';
import { Button } from 'shared/elements/Button';
import { Dialog } from 'shared/layers/Dialog';
import { HubAccountModal } from './HubAccountModal';
import DeleteModal from '../DeleteModal';
import { useMutation } from '@tanstack/react-query';
import Joyride, { Step } from 'react-joyride';
import { theme } from 'shared/utils/DesignTokens';
import { useSetState } from 'react-use';
import styles from '../AWSProvider.module.css';

interface ITourState {
  run: boolean;
  steps: Step[];
}

const HubAccounts = ({ aws, isLoading, refetch, hubAccounts }) => {
  const [showDialog, setShowDialog] = useState(false);
  const [{ run, steps }, setState] = useSetState<ITourState>({
    run: false,
    steps: []
  });

  const newHubBtnRef = useRef();
  const proceedBtnbRef = useRef();

  // useEffect(() => {
  //   if (newHubBtnRef?.current) {
  //     setState({
  //       run: true,
  //       steps: [
  //         {
  //           target: newHubBtnRef.current,
  //           content: (
  //             <p>
  //               Please click on the &apos;Configure&apos; button to set up your
  //               AWS settings and add a new hub role to connect to AWS.
  //             </p>
  //           ),
  //           title: 'Setup AWS',
  //           placement: 'left',
  //           disableBeacon: true,
  //           disableOverlayClose: true,
  //           hideCloseButton: true,
  //           hideFooter: true,
  //           spotlightClicks: true,
  //           styles: {
  //             options: {
  //               zIndex: 10000,
  //               arrowColor: theme.colors.gray[600],
  //               backgroundColor: theme.colors.gray[600],
  //               primaryColor: theme.colors.blue[600],
  //               textColor: theme.colors.white,
  //               overlayColor: theme.colors.gray[700],
  //               width: '450px'
  //             }
  //           }
  //         },
  //       ]
  //     });
  //   }
  //   return () => setState({ run: false });
  // }, [newHubBtnRef, setState]);

  console.log('=========================', proceedBtnbRef);

  useEffect(() => {
    if (proceedBtnbRef?.current) {
      setState({
        run: true,
        steps: [
          {
            target: proceedBtnbRef.current,
            content: (
              <p>
                Please click on the &apos;Configure&apos; button to set up your
                AWS settings and add a new hub role to connect to AWS.
              </p>
            ),
            title: 'Setup AWS',
            placement: 'left',
            disableBeacon: true,
            disableOverlayClose: true,
            hideCloseButton: true,
            hideFooter: true,
            spotlightClicks: true,
            styles: {
              options: {
                zIndex: 10000,
                arrowColor: theme.colors.gray[600],
                backgroundColor: theme.colors.gray[600],
                primaryColor: theme.colors.blue[600],
                textColor: theme.colors.white,
                overlayColor: theme.colors.gray[700],
                width: '450px'
              }
            }
          }
        ]
      });
    }
    return () => setState({ run: false });
  }, [proceedBtnbRef, setState]);

  const { mutateAsync: deleteHubAccountMutation } = useMutation({
    mutationFn: (awsOrganization: HubAccount) =>
      deleteHubAccount(awsOrganization),
    mutationKey: ['deleteHubAccount']
  });

  const tableRows = useMemo(() => {
    return hubAccounts.map(item => ({
      ...item,
      actions: (
        <div className={styles.tableActions}>
          <DeleteModal
            title="Delete Hub Account"
            warningMessage="Are you sure you want to delete this item? This action cannot be undone and all
             associated data will be permanently removed."
            refreshData={refetch}
            onDelete={deleteHubAccountMutation}
            data={item}
          />
        </div>
      )
    }));
  }, [hubAccounts, refetch, deleteHubAccountMutation]);

  return (
    <>
      <Joyride
        hideCloseButton
        run={run}
        hideBackButton
        // continuous
        steps={steps}
        disableScrolling
        styles={{
          options: {
            zIndex: 10000,
            arrowColor: theme.colors.gray[200],
            backgroundColor: theme.colors.gray[700],
            primaryColor: theme.colors.blue[600],
            textColor: theme.colors.gray[100],
            overlayColor: theme.colors.gray[600]
          }
        }}
      />
      <div className={styles.section}>
        <h3 className={styles.header}>Hub Account</h3>
        <div className={styles.content}>
          <div className={styles.headerActions}>
            <Button icon="refresh" onClick={() => refetch()}></Button>
            {!tableRows.length && (
              <Button
                size="small"
                onClick={() => setShowDialog(true)}
                ref={newHubBtnRef}
              >
                New
              </Button>
            )}
          </div>
          <Table
            columns={HubAccountsColumns}
            data={tableRows}
            isLoading={isLoading}
            border="row"
          />
        </div>
        <Dialog
          header="Add Hub Account"
          size="medium"
          setShowDialog={setShowDialog}
          showDialog={showDialog}
        >
          <HubAccountModal
            onClose={() => setShowDialog(false)}
            defaultValues={hubAccounts?.length ? hubAccounts[0] : null}
            aws={aws}
            ref={proceedBtnbRef}
          />
        </Dialog>
      </div>
    </>
  );
};

export default HubAccounts;
