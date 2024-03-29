import React, { useMemo, useState } from 'react'

import { Button, Modal } from 'semantic-ui-react'

export const useModal = (title, onOpen) => {
  const [isOpen, setOpen] = useState(false)

  const openModal = () => {
    if (onOpen) onOpen()
    setOpen(true)
  }
  const closeModal = (onClose) => {
    if (onClose) onClose()
    setOpen(false)
  }

  const ModalComponent = useMemo(
    () =>
      ({
        children,
        onClickToConfirm,
        confirmButtonLabel,
        hideConfirm,
        onClose,
        forceTitle, // TODO: Update all modals to use only the title in prop.
      }) =>
        (
          <Modal open={isOpen}>
            <Modal.Header>{forceTitle}</Modal.Header>
            <Modal.Content>{children}</Modal.Content>
            <Modal.Actions>
              <Button onClick={() => closeModal(onClose)}>Close</Button>
              {!hideConfirm && (
                <Button onClick={onClickToConfirm} positive>
                  {confirmButtonLabel || 'Confirm'}
                </Button>
              )}
            </Modal.Actions>
          </Modal>
        ),
    [isOpen]
  )

  return {
    openModal,
    closeModal,
    ModalComponent,
  }
}
