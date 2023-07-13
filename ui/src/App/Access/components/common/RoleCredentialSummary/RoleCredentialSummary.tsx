import { FC, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';

import styles from './RoleCredentialSummary.module.css';
import { HEADER_FIXED_HIEGHT, ROLE_SUMMARY_LINKS } from './constants';
import { getRoleCredentials } from 'core/API/roles';
import { CodeBlock } from 'shared/elements/CodeBlock';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { useIntersection } from 'react-use';
import { useQuery } from '@tanstack/react-query';

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
    [noqCLIIntersection]
  );

  useEffect(
    function onAwsProfileIntersection() {
      if (awsProfileIntersection?.isIntersecting) {
        setActiveLink(ROLE_SUMMARY_LINKS.AWS_PROFILE);
      }
    },
    [awsProfileIntersection]
  );

  useEffect(
    function onEnvironmentVariableIntersection() {
      if (environmentVariableIntersection?.isIntersecting) {
        setActiveLink(ROLE_SUMMARY_LINKS.ENVIRONMENT_VARIABLES);
      }
    },
    [environmentVariableIntersection]
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

      dialogRef?.current.scrollTo({
        top: activeRef?.current.offsetTop - HEADER_FIXED_HIEGHT,
        behavior: 'smooth'
      });
    },
    [awsProfileRef, dialogRef, environmentVariablesRef, noqCLIRef]
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
                    className={`${styles.navItem} ${
                      activeLink === ROLE_SUMMARY_LINKS.NOQ_CLI
                        ? styles.active
                        : ''
                    }`}
                    onClick={() => handleOnClick(ROLE_SUMMARY_LINKS.NOQ_CLI)}
                  >
                    Noq CLI
                  </li>
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
                    AWS Profile
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
              <p className={styles.secondaryText}>
                To retrieve AWS credentials on demand
              </p>
              <div className={styles.subHeader}>Credential Process</div>
              <CodeBlock
                code={`noq credential_process -g
export AWS_PROFILE=${role}`}
              />
              <div className={styles.subHeader}>ECS Credential Provider</div>
              <CodeBlock
                code={`noq serve & export AWS_CONTAINER_CREDENTIALS_FULL_URI=http://127.0.0.1:9091/ecs/${arn} `}
              />

              <div className={styles.subHeader}>Write Credentials to File</div>
              <CodeBlock
                code={`noq file -p ${role} ${arn}
export AWS_PROFILE=${role}`}
              />

              <div className={styles.subHeader}>Credential Export</div>
              <div className={styles.codeBlock}>
                <CodeBlock code={`noq export ${arn}`} />
              </div>

              <div
                className={styles.sectionHeader}
                ref={environmentVariablesRef}
              >
                Environment Variables
              </div>
              <p className={styles.secondaryText}>
                To configure your workspace
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
                AWS Profile
              </div>
              <p className={styles.secondaryText}>
                Add a profile in your AWS credentials file
              </p>
              {crendentials ? (
                <CodeBlock
                  code={`[${role}]
aws_access_key_id=${crendentials?.AccessKeyId}
aws_secret_access_key=${crendentials?.SecretAccessKey}
aws_session_token=${crendentials?.SessionToken}`}
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
            </div>
          </div>
        </div>
      </Dialog>
    </>
  );
};

export default RoleCredentialSummary;
