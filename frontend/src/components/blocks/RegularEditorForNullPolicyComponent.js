import React from 'react'
import { GridColumn } from 'semantic-ui-react'
import Editor from '@monaco-editor/react'
import { NullPolicyNotification } from './notificationMessages'

const RegularEditorForNullPolicyComponent = (props) => {
  const { isNullPolicy, language, oldValue, editorTheme } = props
  return (
    <div>
      <GridColumn>
        <Editor
          defaultLanguage={language}
          width='100%'
          height='500px'
          defaultValue={oldValue}
          //onMount={editorDidMount}
          //options={options}
          //onChange={onChange}
          theme={editorTheme}
          alwaysConsumeMouseWheel={false}
        />
      </GridColumn>
      <GridColumn>
        <NullPolicyNotification isNullPolicy={isNullPolicy} />
      </GridColumn>
    </div>
  )
}
