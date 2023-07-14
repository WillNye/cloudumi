import { FC, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';

import { HEADER_FIXED_HIEGHT, ROLE_SUMMARY_LINKS } from './constants';
import { getRoleCredentials } from 'core/API/roles';
import { CodeBlock } from 'shared/elements/CodeBlock';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { useIntersection } from 'react-use';
import { useQuery } from '@tanstack/react-query';
import { LineBreak } from 'shared/elements/LineBreak';
import classNames from 'classnames';
import styles from './RoleCredentialSummary.module.css';

type RoleCredentialSummaryProps = {
  arn: string;
  accountName: string;
  roleName: string;
};

type AWSCredentials = {
  AccessKeyId: string;
  SecretAccessKey: string;
  SessionToken: string;
  Expiration: number;
};

const RoleCredentialSummary: FC<RoleCredentialSummaryProps> = ({
  arn,
  roleName,
  accountName
}) => {
  const [showDialog, setShowDialog] = useState(false);
  const [activeLink, setActiveLink] = useState(ROLE_SUMMARY_LINKS.NOQ_CLI);
  const [crendentials, setCredentials] = useState<AWSCredentials | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const credentialProcessRef = useRef<HTMLDivElement>();
  const credentialsProviderRef = useRef<HTMLDivElement>();
  const writeCredentialsRef = useRef<HTMLDivElement>();
  const credentialExportRef = useRef<HTMLDivElement>();

  const dialogRef = useRef<HTMLDivElement>();
  const noqCLIRef = useRef<HTMLDivElement>();
  const environmentVariablesRef = useRef<HTMLDivElement>();
  const awsProfileRef = useRef<HTMLDivElement>();

  const noqCLIIntersection = useIntersection(noqCLIRef, {});
  const awsProfileIntersection = useIntersection(awsProfileRef, {});
  const environmentVariableIntersection = useIntersection(
    environmentVariablesRef,
    {}
  );

  useEffect(
    function onNoqCLIIntersection() {
      if (noqCLIIntersection?.isIntersecting) {
        setActiveLink(ROLE_SUMMARY_LINKS.NOQ_CLI);
      }
    },
    [noqCLIIntersection?.isIntersecting]
  );

  useEffect(
    function onAwsProfileIntersection() {
      if (awsProfileIntersection?.isIntersecting) {
        setActiveLink(ROLE_SUMMARY_LINKS.AWS_PROFILE);
      }
    },
    [awsProfileIntersection?.isIntersecting]
  );

  useEffect(
    function onEnvironmentVariableIntersection() {
      if (environmentVariableIntersection?.isIntersecting) {
        setActiveLink(ROLE_SUMMARY_LINKS.ENVIRONMENT_VARIABLES);
      }
    },
    [environmentVariableIntersection?.isIntersecting]
  );

  const role = useMemo(
    () => `${accountName}/${roleName}`,
    [accountName, roleName]
  );

  const { refetch, isFetching: isLoading } = useQuery({
    enabled: false,
    queryFn: getRoleCredentials,
    queryKey: ['getRoleCredentials', { requested_role: arn }],
    onSuccess: data => {
      setCredentials(data.Credentials);
    },
    onError: () => {
      setErrorMsg('Unable to get AWS Credentials for this role');
    }
  });

  useEffect(
    function onMount() {
      if (showDialog) {
        refetch();
      }
    },
    [showDialog, refetch]
  );

  const scrollToRef = useCallback(
    activeRef => {
      dialogRef?.current.scrollTo({
        top: activeRef?.current.offsetTop - HEADER_FIXED_HIEGHT,
        behavior: 'smooth'
      });
    },
    [dialogRef]
  );

  const handleOnClick = useCallback(
    (newLink: ROLE_SUMMARY_LINKS) => {
      setActiveLink(newLink);

      let activeRef = noqCLIRef;

      if (newLink === ROLE_SUMMARY_LINKS.ENVIRONMENT_VARIABLES) {
        activeRef = environmentVariablesRef;
      }

      if (newLink === ROLE_SUMMARY_LINKS.AWS_PROFILE) {
        activeRef = awsProfileRef;
      }
      scrollToRef(activeRef);
    },
    [awsProfileRef, environmentVariablesRef, noqCLIRef, scrollToRef]
  );

  return (
    <>
      <div
        className={styles.pointer}
        onClick={() => setShowDialog(!showDialog)}
      >
        <Icon name="break-glass" size="large" color="secondary" />
      </div>
      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        size="large"
        disablePadding
        header="Code and Comands"
        isLoading={isLoading}
      >
        <div className={styles.roleSummary}>
          <div className={styles.content}>
            <div className={styles.sideNav}>
              <nav className={styles.nav}>
                <ul className={styles.navList}>
                  <li
                    className={classNames(styles.navItem, {
                      [styles.active]: activeLink === ROLE_SUMMARY_LINKS.NOQ_CLI
                    })}
                    onClick={() => handleOnClick(ROLE_SUMMARY_LINKS.NOQ_CLI)}
                  >
                    Noq CLI
                  </li>
                  <ul className={styles.subNavList}>
                    <li
                      className={styles.subNavItem}
                      onClick={() => {
                        setActiveLink(ROLE_SUMMARY_LINKS.NOQ_CLI);
                        scrollToRef(credentialProcessRef);
                      }}
                    >
                      Credential Process
                    </li>
                    <li
                      className={styles.subNavItem}
                      onClick={() => {
                        scrollToRef(credentialsProviderRef);
                        setActiveLink(ROLE_SUMMARY_LINKS.NOQ_CLI);
                      }}
                    >
                      ECS Credential Provider
                    </li>
                    <li
                      className={styles.subNavItem}
                      onClick={() => {
                        scrollToRef(writeCredentialsRef);
                        setActiveLink(ROLE_SUMMARY_LINKS.NOQ_CLI);
                      }}
                    >
                      Write Credentials to File
                    </li>
                    <li
                      className={styles.subNavItem}
                      onClick={() => {
                        setActiveLink(ROLE_SUMMARY_LINKS.NOQ_CLI);
                        scrollToRef(credentialExportRef);
                      }}
                    >
                      Credential Export
                    </li>
                  </ul>
                  <li
                    className={`${styles.navItem} ${
                      activeLink === ROLE_SUMMARY_LINKS.ENVIRONMENT_VARIABLES
                        ? styles.active
                        : ''
                    }`}
                    onClick={() =>
                      handleOnClick(ROLE_SUMMARY_LINKS.ENVIRONMENT_VARIABLES)
                    }
                  >
                    Environment Vars
                  </li>
                  <li
                    className={`${styles.navItem} ${
                      activeLink === ROLE_SUMMARY_LINKS.AWS_PROFILE
                        ? styles.active
                        : ''
                    }`}
                    onClick={() =>
                      handleOnClick(ROLE_SUMMARY_LINKS.AWS_PROFILE)
                    }
                  >
                    AWS Credentials File
                  </li>
                </ul>
              </nav>
            </div>
            <div className={styles.container} ref={dialogRef}>
              <div>
                <p>
                  Use the appropriate set of commands to configure AWS
                  credentials for your environment.
                </p>
              </div>
              <div className={styles.sectionHeader} ref={noqCLIRef}>
                Noq CLI
              </div>
              <div className={styles.subHeader} ref={credentialProcessRef}>
                Credential Process
              </div>
              Run the following command to configure credential_process. This
              only needs to be run once or as you gain access to new roles.
              <LineBreak />
              <CodeBlock code={`noq credential_process -g`} />
              <LineBreak />
              Set the following environment variables to instruct the AWS CLI to
              use the credential_process flow that is defined in your
              ~/.aws/config file. Ensure that the profile name isn&apos;t also
              configured in your ~/.aws/credentials file. This method
              automatically refreshes credentials when they expire, as long as
              your credentials to the Noq platform are still valid.
              <LineBreak />
              <CodeBlock code={`export AWS_PROFILE=${role}`} />
              <div className={styles.subHeader} ref={credentialsProviderRef}>
                ECS Credential Provider
              </div>
              In another terminal or background process, run the following
              command:
              <LineBreak />
              <CodeBlock code={`noq serve`} />
              <LineBreak />
              Set the following environment variable in your terminal or IDE to
              instruct the AWS CLI to retrieve credentials from Noq CLI&apos;s
              ECS Credential Provider. This method automatically refreshes
              credentials when they expire, as long as your credentials to the
              Noq platform are still valid.
              <LineBreak />
              <CodeBlock
                code={`export AWS_CONTAINER_CREDENTIALS_FULL_URI=http://127.0.0.1:9091/ecs/${arn}`}
              />
              <LineBreak />
              <div className={styles.subHeader} ref={writeCredentialsRef}>
                Write Credentials to File
              </div>
              Use the Noq CLI to write temporary credentials to your
              ~/.aws/credentials file. These credentials will expire, and you
              will need to run the command again to refresh them.
              <LineBreak />
              <CodeBlock
                code={`noq file -p ${role} ${arn}
export AWS_PROFILE=${role}`}
              />
              <LineBreak />
              <div className={styles.subHeader} ref={credentialExportRef}>
                Credential Export
              </div>
              <div className={styles.codeBlock}>
                Use the Noq CLI to export temporary credentials as environment
                variables. These credentials will expire, and you will need to
                run the command again to refresh them.
                <LineBreak />
                <CodeBlock code={`noq export ${arn}`} />
                <LineBreak />
                Use the following command to set the environment variables in
                your current terminal session:
                <LineBreak />
                <CodeBlock code={`eval $(noq export ${arn})`} />
              </div>
              <div
                className={styles.sectionHeader}
                ref={environmentVariablesRef}
              >
                Environment Variables
              </div>
              <LineBreak />
              <p className={styles.secondaryText}>
                To source credentials without using the Noq CLI, use the
                following environment variables:
              </p>
              {crendentials ? (
                <CodeBlock
                  code={`export AWS_ACCESS_KEY_ID=${crendentials?.AccessKeyId}
export AWS_SECRET_ACCESS_KEY=${crendentials?.SecretAccessKey}
export AWS_SESSION_TOKEN=${crendentials?.SessionToken}`}
                />
              ) : (
                <Notification
                  header="Missing credentials"
                  type={NotificationType.WARNING}
                  message={errorMsg}
                  showCloseIcon={false}
                  fullWidth
                />
              )}
              <div ref={awsProfileRef} className={styles.sectionHeader}>
                AWS Credentials Profile
              </div>
              <LineBreak />
              <p className={styles.secondaryText}>
                The following should be manually added to your
                ~/.aws/credentials file:
              </p>
              {crendentials ? (
                <>
                  <CodeBlock
                    code={`[${role}]
aws_access_key_id=${crendentials?.AccessKeyId}
aws_secret_access_key=${crendentials?.SecretAccessKey}
aws_session_token=${crendentials?.SessionToken}`}
                  />
                  Use these credentials by setting the AWS_PROFILE environment
                  variable:
                  <LineBreak />
                  <CodeBlock code={`export AWS_PROFILE=${role}`} />
                </>
              ) : (
                <Notification
                  header="Missing credentials"
                  type={NotificationType.WARNING}
                  message={errorMsg}
                  showCloseIcon={false}
                  fullWidth
                />
              )}
            </div>
          </div>
        </div>
      </Dialog>
    </>
  );
};

export default RoleCredentialSummary;
