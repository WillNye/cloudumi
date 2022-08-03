/* eslint-disable no-use-before-define */

import React, { useMemo, useState } from 'react'
import { DiffEditor } from '@monaco-editor/react'
import { getLocalStorageSettings } from 'helpers/utils'
import { DoubleViewHeader } from './BlockHeader'
import { Button, Icon } from 'semantic-ui-react'
import { DEFAULT_EDITOR_OPTIONS } from './constants'
import './DiffEditorBlock.scss'

const DiffEditorBlock = (props) => {
  const { diffChanges } = props

  const [renderSideBySide, setRenderSideBySide] = useState(true)

  const editorTheme = getLocalStorageSettings('editorTheme')
  const options = useMemo(
    () => ({ ...DEFAULT_EDITOR_OPTIONS, renderSideBySide }),
    [renderSideBySide]
  )

  return (
    <div className='editor-block'>
      <div className='editor-block__render_style'>
        <Button.Group>
          <Button
            icon
            color={renderSideBySide ? 'grey' : 'white'}
            onClick={() => setRenderSideBySide(true)}
          >
            <Icon size='large' name='columns' />
          </Button>
          <Button
            icon
            color={renderSideBySide ? 'white' : 'grey'}
            onClick={() => setRenderSideBySide(false)}
          >
            <Icon size='large' name='square outline' />
          </Button>
        </Button.Group>
      </div>

      <div>
        <DoubleViewHeader diffChanges={diffChanges} />
      </div>

      <DiffEditor
        language='json'
        width='100%'
        height='600px'
        original={JSON.stringify(
          diffChanges.oldVersion?.config_change || {},
          null,
          2
        )}
        modified={JSON.stringify(
          diffChanges.newVersion?.config_change || {},
          null,
          2
        )}
        options={options}
        theme={editorTheme}
      />
    </div>
  )
}

export default DiffEditorBlock
