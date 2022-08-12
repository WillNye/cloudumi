import { useToast } from 'lib/Toast'
import React from 'react'
import { Button, Icon } from 'semantic-ui-react'
import { formatISODate } from '../../utils'

export const SingleViewHeader = ({ change }) => {
  const { error, success } = useToast()

  const handleCopyToClipBoard = () => {
    const text = JSON.stringify(change.config_change)
    navigator.clipboard.writeText(text).then(
      () => {
        success('Copied to clipboard')
      },
      () => {
        error('Unable to copy resource history')
      }
    )
  }

  return (
    <div className='editor-block__blocK_header'>
      {change ? (
        <>
          <h4>{formatISODate(change.updated_at)}</h4>
          <div className='editor-block__blocK_header__text'>
            <div>
              <div>
                Changed By : <span>____</span>
              </div>
              <div>
                Session Name : <span>_____</span>
              </div>
            </div>
            <Button icon onClick={handleCopyToClipBoard}>
              <Icon name='outline copy'></Icon>
            </Button>
          </div>
        </>
      ) : (
        <h4>Select a version from the timeline</h4>
      )}
    </div>
  )
}

export const AssociatedPolicyHeader = ({ change }) => {
  const { error, success } = useToast()

  const handleCopyToClipBoard = () => {
    const text = JSON.stringify(change.config_change)
    navigator.clipboard.writeText(text).then(
      () => {
        success('Copied to clipboard')
      },
      () => {
        error('Unable to copy resource history')
      }
    )
  }

  return (
    <div className='editor-block__associated_blocK_header'>
      {change ? (
        <>
          <h3>{change.config_change.resourceName}</h3>
          <div className='editor-block__associated_blocK_header__text'>
            <div>
              <div>
                Updated On : <span>{formatISODate(change.updated_at)}</span>
              </div>
              <div>
                Changed By : <span>____</span>
              </div>
              <div>
                Session Name : <span>_____</span>
              </div>
            </div>
            <Button icon onClick={handleCopyToClipBoard}>
              <Icon name='outline copy'></Icon>
            </Button>
          </div>
        </>
      ) : (
        <h4>Select a version from the timeline</h4>
      )}
    </div>
  )
}

export const DoubleViewHeader = ({
  diffChanges,
  renderSideBySide,
  associatedHistoryChange,
}) => {
  return (
    <div className='editor-block__double_view_header'>
      {associatedHistoryChange ? (
        <AssociatedPolicyHeader change={associatedHistoryChange} />
      ) : (
        <>
          <SingleViewHeader change={diffChanges.oldVersion} />
          <SingleViewHeader change={diffChanges.newVersion} />
        </>
      )}
    </div>
  )
}
