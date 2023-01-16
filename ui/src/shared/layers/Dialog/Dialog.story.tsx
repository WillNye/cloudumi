import { useDialog } from 'reablocks';
import { Dialog } from './Dialog';
import { Button } from '../../elements/Button';
import { useState } from 'react';

export default {
  title: 'Layers/Dialog',
  component: Dialog
};

export const Simple = () => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <>
      <Button onClick={() => setShowDialog(!showDialog)}>Open Dialog</Button>
      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        header="Whats up"
        size="small"
      >
        Hello
      </Dialog>
    </>
  );
};

const CustomHeaderElement = ({ children }: any) => <h4>Custom Header</h4>;

export const CustomHeader = () => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <div style={{ textAlign: 'center', margin: '50px' }}>
      <Button onClick={() => setShowDialog(!showDialog)}>Open Dialog</Button>
      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        header={<CustomHeaderElement />}
        size="small"
      >
        Body Content
      </Dialog>
    </div>
  );
};

export const Sizes = () => {
  const [showDialogSmall, setShowDialogSmall] = useState(false);
  const [showDialogMeduim, setShowDialogMedium] = useState(false);
  const [showDialogLarge, setShowDialogLarge] = useState(false);

  return (
    <>
      <Button onClick={() => setShowDialogSmall(!showDialogSmall)}>
        Open Small
      </Button>
      <Dialog
        showDialog={showDialogSmall}
        setShowDialog={setShowDialogSmall}
        header="Whats up"
        size="small"
      >
        Hello Small
      </Dialog>
      <br />
      <br />
      <Button onClick={() => setShowDialogMedium(!showDialogMeduim)}>
        Open Meduim
      </Button>
      <Dialog
        showDialog={showDialogMeduim}
        setShowDialog={setShowDialogMedium}
        header="Whats up"
        size="medium"
      >
        Hello Meduim
      </Dialog>
      <br />
      <br />
      <Button onClick={() => setShowDialogLarge(!showDialogLarge)}>
        Open Large
      </Button>
      <Dialog
        showDialog={showDialogLarge}
        setShowDialog={setShowDialogLarge}
        header="Whats up"
        size="large"
      >
        Hello Large
      </Dialog>
    </>
  );
};
