import { useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';

const UserModal = () => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <div>
      <div onClick={() => setShowDialog(true)}>
        <Icon name="edit" size="medium" />
      </div>

      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        header="user Modal"
      >
        <div>Users</div>
      </Dialog>
    </div>
  );
};

export default UserModal;
