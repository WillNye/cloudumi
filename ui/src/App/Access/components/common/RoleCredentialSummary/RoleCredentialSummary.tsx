import { FC, useCallback, useEffect, useRef, useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';

import styles from './RoleCredentialSummary.module.css';
import { HEADER_FIXED_HIEGHT, ROLE_SUMMARY_LINKS } from './constants';
import { getRoleCredentials } from 'core/API/roles';
import { CodeBlock } from 'shared/elements/CodeBlock';
import { Notification, NotificationType } from 'shared/elements/Notification';

type RoleCredentialSummaryProps = {
  arn: string;
  role: string;
};

type AWSCredentials = {
  AccessKeyId: string;
  SecretAccessKey: string;
  SessionToken: string;
  Expiration: number;
};

const RoleCredentialSummary: FC<RoleCredentialSummaryProps> = ({
  arn,
  role
}) => {
  const [showDialog, setShowDialog] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeLink, setActiveLink] = useState(ROLE_SUMMARY_LINKS.NOQ_CLI);
  const [crendentials, setCredentials] = useState<AWSCredentials | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(
    function onMount() {
      if (showDialog) {
        const role = {
          requested_role: arn
        };
        setIsLoading(true);
        getRoleCredentials(role)
          .then(({ data }) => {
            setCredentials(data.Credentials);
          })
          .catch(error => {
            setErrorMsg('Unable to get AWS Credentials for this role');
          })
          .finally(() => {
            setIsLoading(false);
          });
      }
    },
    [arn, showDialog]
  );

  const dialogRef = useRef<HTMLDivElement>();
  const noqCLIRef = useRef<HTMLDivElement>();
  const environmentVariablesRef = useRef<HTMLDivElement>();
  const awsProfileRef = useRef<HTMLDivElement>();

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
        size="medium"
        disablePadding
        header="Code and Comands"
        ref={dialogRef}
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
            <div className={styles.container}>
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
              <CodeBlock>
                <p>{`noq credential_process -g ${role}`}</p>
                <p>{`export AWS_PROFILE=${role}`}</p>
              </CodeBlock>

              <div className={styles.subHeader}>ECS Credential Provider</div>
              <CodeBlock>
                <p>
                  noq serve & export
                  AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9091/ecs/prod/prod_admin
                </p>
              </CodeBlock>

              <div className={styles.subHeader}>Write Credentials to File</div>
              <CodeBlock>
                <p>{`noq file -p ${role}`}</p>
                <p>{`export AWS_PROFILE=${role}`}</p>
              </CodeBlock>

              <div className={styles.subHeader}>Credential Export</div>
              <div className={styles.codeBlock}>
                <CodeBlock>{`noq export ${role}`}</CodeBlock>
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
                <CodeBlock>
                  <p>export AWS_ACCESS_KEY_ID={crendentials?.AccessKeyId}</p>
                  <p>
                    export AWS_SECRET_ACCESS_KEY={crendentials?.SecretAccessKey}
                  </p>
                  <p>export AWS_SESSION_TOKEN={crendentials?.SessionToken}</p>
                </CodeBlock>
              ) : (
                <Notification
                  header="Missing credentials"
                  type={NotificationType.WARNING}
                  message={errorMsg}
                  showCloseIcon={false}
                />
              )}

              <div ref={awsProfileRef} className={styles.sectionHeader}>
                AWS Profile
              </div>
              <p className={styles.secondaryText}>
                Add a profile in your AWS credentials file
              </p>
              {crendentials ? (
                <CodeBlock>
                  <p>{`[${role}]`}</p>
                  <p>aws_access_key_id={crendentials?.AccessKeyId}</p>
                  <p>aws_secret_access_key={crendentials?.SecretAccessKey}</p>
                  <p>aws_session_token={crendentials?.SessionToken}</p>
                </CodeBlock>
              ) : (
                <Notification
                  header="Missing credentials"
                  type={NotificationType.WARNING}
                  message={errorMsg}
                  showCloseIcon={false}
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
