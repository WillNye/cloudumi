import { useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';

const GroupsModal = () => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <div>
      <div onClick={() => setShowDialog(true)}>
        <Icon name="edit" size="medium" />
      </div>

      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        header="Group Modal"
      >
        <div>Groups</div>
      </Dialog>
    </div>
  );
};

export default GroupsModal;
