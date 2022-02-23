import React, { useState } from 'react';

import { Button, Modal } from 'semantic-ui-react';

export const useModal = (title, onOpen, onClose) => {
  
  const [isOpen, setOpen] = useState(false);

  const openModal = () => {
    if (onOpen) onOpen();
    setOpen(true);
  };
  const closeModal = () => {
    if (onClose) onClose();
    setOpen(false);
  };

  const ModalComponent = ({ children, onClickToConfirm, confirmButtonLabel }) => (
    <Modal open={isOpen}>
      <Modal.Header>{title}</Modal.Header>
      <Modal.Content>
        {children}
      </Modal.Content>
      <Modal.Actions>
        <Button onClick={() => setOpen(false)}>
          Cancel
        </Button>
        <Button onClick={onClickToConfirm} positive>
          {confirmButtonLabel || 'Confirm'}
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