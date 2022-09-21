import React from 'react'
import Editor from '@monaco-editor/react'
import { NullPolicyNotification } from './notificationMessages'

export const RegularEditorForNullPolicyComponent = (props) => {
  const { isNullPolicy, language, currentPolicy, editorTheme } = props

  return (
    <div className='center-elements'>
      <div className='section-width'>
        <Editor
          key='regular-editor-for-null-policy'
          defaultLanguage={language}
          width='100%'
          height='500px'
          defaultValue={currentPolicy}
          theme={editorTheme}
          alwaysConsumeMouseWheel={false}
          className=''
        />
      </div>

      <div className='section-width'>
        <NullPolicyNotification isNullPolicy={isNullPolicy} />
      </div>
    </div>
  )
}
