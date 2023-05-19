import { Dialog } from './Dialog';
import { Button } from '../../elements/Button';
import { useState } from 'react';
import { LineBreak } from 'shared/elements/LineBreak';

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
      <LineBreak size="large" />
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
      <LineBreak size="large" />
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
