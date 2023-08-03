import { useState, useRef, FC } from 'react';
import { Button } from 'shared/elements/Button';
import { Icon } from 'shared/elements/Icon';
import { Menu } from 'shared/layers/Menu';
import RoleAccessPreferencesModal from '../RoleAccessPreferencesModal/RoleAccessPreferencesModal';

import styles from './MoreActions.module.css';

interface MoreActionsProps {
  role: { secondary_resource_id: string };
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
