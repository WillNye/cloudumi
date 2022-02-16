import React, { useState } from 'react';

import { Button, Modal } from 'semantic-ui-react';

export const useModal = (title) => {
  
  const [isOpen, setOpen] = useState(false);

  const openModal = () => setOpen(true);
  const closeModal = () => setOpen(false);

  const ModalComponent = ({ children, onClickToSave }) => (
    <Modal open={isOpen}>
      <Modal.Header>{title}</Modal.Header>
      <Modal.Content>
        {children}
      </Modal.Content>
      <Modal.Actions>
        <Button onClick={() => setOpen(false)}>
          Cancel
        </Button>
        <Button onClick={onClickToSave} positive>
          Save
        </Button>
      </Modal.Actions>          
    </Modal>
  );

  return {
    openModal,
    closeModal,
    ModalComponent
  };
};