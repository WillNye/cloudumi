import React from 'react'
import { Button, Icon } from 'semantic-ui-react'
import { formatISODate } from '../../utils'

export const SingleViewHeader = ({ change }) => {
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
            <Button icon>
              <Icon name='outline copy'></Icon>
            </Button>
          </div>
        </>
      ) : (
        <h3>Select a version from the timeline</h3>
      )}
    </div>
  )
}

export const DoubleViewHeader = ({ diffChanges }) => {
  return (
    <div className='editor-block__double_view_header'>
      <SingleViewHeader change={diffChanges.oldVersion} />
      <SingleViewHeader change={diffChanges.newVersion} />
    </div>
  )
}
