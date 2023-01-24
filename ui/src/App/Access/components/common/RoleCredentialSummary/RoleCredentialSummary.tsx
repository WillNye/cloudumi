import { useCallback, useRef, useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';

import styles from './RoleCredentialSummary.module.css';
import { ROLE_SUMMARY_LINKS } from './constants';
import { useCopyToClipboard } from 'react-use';

const RoleCredentialSummary = () => {
  const [showDialog, setShowDialog] = useState(false);
  const [activeLink, setActiveLink] = useState(ROLE_SUMMARY_LINKS.NOQ_CLI);

  const [copiedText, copyText] = useCopyToClipboard();

  const dialogRef = useRef<HTMLDivElement>();
  const noqCLIRef = useRef<HTMLDivElement>();
  const environmentVariablesRef = useRef<HTMLDivElement>();
  const awsProfileRef = useRef<HTMLDivElement>();

  const handleOnClick = useCallback(
    (newLink: ROLE_SUMMARY_LINKS) => {
      setActiveLink(newLink);

      let activeRef;

      if (newLink === ROLE_SUMMARY_LINKS.NOQ_CLI) {
        activeRef = noqCLIRef;
      }

      if (newLink === ROLE_SUMMARY_LINKS.ENVIRONMENT_VARIABLES) {
        activeRef = environmentVariablesRef;
      }

      if (newLink === ROLE_SUMMARY_LINKS.AWS_PROFILE) {
        activeRef = awsProfileRef;
      }

      dialogRef?.current.scrollTo({
        top: activeRef?.current.offsetTop,
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
                {/* <Icon name="info" size="medium" /> */}
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
              <div className={styles.codeBlock}>
                <p>noq credential_process -g prod/prod_admin</p>
                <p>export AWS_PROFILE=prod/prod_admin</p>
              </div>

              <div className={styles.subHeader}>ECS Credential Provider</div>
              <div className={styles.codeBlock}>
                <p>
                  noq serve & export
                  AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9091/ecs/prod/prod_admin
                </p>
              </div>

              <div className={styles.subHeader}>Write Credentials to File</div>
              <div className={styles.codeBlock}>
                <p>noq file -p prod/prod_admin prod/prod_admin</p>
                <p>export AWS_PROFILE=prod/prod_admin</p>
              </div>

              <div className={styles.subHeader}>Credential Export</div>
              <div className={styles.codeBlock}>
                <p>noq export prod/prod_admin</p>
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
              <div className={styles.codeBlock}>
                <p>export AWS_ACCESS_KEY_ID=ASIAYOLWP5232BHVOPPI</p>
                <p>export AWS_SECRET_ACCESS_KEY=5YT0Ibw3vp1nxYIBM...</p>
                <p>export AWS_SESSION_TOKEN=IQoJb3JpZ2luX2VjEDAaCX....</p>
              </div>

              <div ref={awsProfileRef} className={styles.sectionHeader}>
                AWS Profile
              </div>
              <p className={styles.secondaryText}>
                Add a profile in your AWS credentials file
              </p>
              <div className={styles.codeBlock}>
                <p>aws_access_key_id=ASIAYOLWP5232BHVOPPI</p>
                <p>aws_secret_access_key=5YT0Ibw3vp1nxYIBM...</p>
                <p>aws_session_token=IQoJb3JpZ2luX2VjEDAaCX....</p>
              </div>
            </div>
          </div>
        </div>
      </Dialog>
    </>
  );
};

export default RoleCredentialSummary;
