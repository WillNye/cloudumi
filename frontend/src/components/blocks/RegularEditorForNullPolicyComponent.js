import React from 'react'
import { Grid } from 'semantic-ui-react'
import Editor from '@monaco-editor/react'
import { NullPolicyNotification } from './notificationMessages'

export const RegularEditorForNullPolicyComponent = (props) => {
  const { isNullPolicy, language, currentPolicy, editorTheme } = props
  return (
    <Grid relaxed columns={2} divided>
      <Grid.Row>
        <Grid.Column>
          <Editor
            key='regular-editor-for-null-policy'
            defaultLanguage={language}
            width='100%'
            height='500px'
            defaultValue={currentPolicy}
            theme={editorTheme}
            alwaysConsumeMouseWheel={false}
          />
        </Grid.Column>
        <Grid.Column>
          <NullPolicyNotification isNullPolicy={isNullPolicy} />
        </Grid.Column>
      </Grid.Row>
    </Grid>
  )
}
