import { useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';

import styles from './RoleCredentialSummary.module.css';
import { Button } from 'shared/elements/Button';

const RoleCredentialSummary = () => {
  const [showDialog, setShowDialog] = useState(false);

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
      >
        <div className={styles.roleSummary}>
          <div className={styles.header}>
            <div>Code and Comands</div>
            <div
              className={styles.pointer}
              onClick={() => setShowDialog(false)}
            >
              <Icon name="close" size="large" />
            </div>
          </div>

          <div className={styles.content}>
            <div className={styles.sideNav}>
              <nav className={styles.nav}>
                <ul className={styles.navList}>
                  <li className={styles.navItem}>
                    <Button variant="text">Noq CLI</Button>
                  </li>
                  <li className={styles.navItem}>
                    <Button variant="text">Environment Vars</Button>
                  </li>
                  <li className={styles.navItem}>
                    <Button variant="text">AWS Profile</Button>
                  </li>
                  <li className={styles.navItem}>
                    <Button variant="text">Credentials</Button>
                  </li>
                </ul>
              </nav>
            </div>
            <div className={styles.container}>
              <div>
                Use the appropriate set of commands to configure AWS credentials
                for your environment.
              </div>
              <div className={styles.subHeader}>Noq CLI</div>
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
              <p className={styles.secondaryText}>noq export prod/prod_admin</p>
            </div>
          </div>
        </div>
      </Dialog>
    </>
  );
};

export default RoleCredentialSummary;
