import { useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';

const Delete = () => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <div>
      <div onClick={() => setShowDialog(true)}>
        <Icon name="delete" size="medium" />
      </div>
      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        header="Delete Modal"
      >
        <div>Delete</div>
      </Dialog>
    </div>
  );
};

export default Delete;
