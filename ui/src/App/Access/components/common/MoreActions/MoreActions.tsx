import { useState, useRef, FC } from 'react';
import { Button } from 'shared/elements/Button';
import { Icon } from 'shared/elements/Icon';
import { Menu } from 'shared/layers/Menu';
import RoleAccessPreferencesModal from '../RoleAccessPreferencesModal/RoleAccessPreferencesModal';

import styles from './MoreActions.module.css';

interface MoreActionsProps {
  role: { arn: string; inactive_tra: boolean };
}

const MoreActions: FC<MoreActionsProps> = ({ role }) => {
  const [open, setOpen] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);
  const buttonRef = useRef(null);

  return (
    <>
      <div
        ref={buttonRef}
        className={styles.pointer}
        onClick={() => setOpen(!open)}
      >
        <Icon name="more" size="large" color="secondary" />
      </div>
      <Menu open={open} onClose={() => setOpen(false)} reference={buttonRef}>
        <div>
          <Button
            variant="text"
            color="secondary"
            size="small"
            fullWidth
            onClick={() => setShowPreferences(true)}
          >
            Preferences
          </Button>
          {/* <Button variant="text" color="secondary" size="small" fullWidth>
            Add Permissions
          </Button>
          <Button variant="text" color="secondary" size="small" fullWidth>
            View Details
          </Button> */}
        </div>
      </Menu>
      {role && showPreferences && (
        <RoleAccessPreferencesModal
          role={role}
          showDialog={showPreferences}
          setShowDialog={setShowPreferences}
        />
      )}
    </>
  );
};

export default MoreActions;
