import { useModal } from 'lib/hooks/useModal'
import { Button } from 'semantic-ui-react'
import { helpContent } from './helpContent'

export const useHelpModal = () => {
  const { openModal, ModalComponent } = useModal('Help')

  const QuestionMark = ({ handler }) => {
    const Content = helpContent(handler)?.Content
    const renderContent = Content ? <Content /> : null
    return (
      <>
        <Button
          size='mini'
          circular
          icon='question'
          basic
          onClick={openModal}
        />
        <ModalComponent hideConfirm>{renderContent}</ModalComponent>
      </>
    )
  }

  return {
    QuestionMark,
  }
}
