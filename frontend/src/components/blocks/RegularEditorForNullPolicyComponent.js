import React from 'react'
import { Grid, GridColumn, GridRow } from 'semantic-ui-react'
import Editor from '@monaco-editor/react'
import { NullPolicyNotification } from './notificationMessages'

export const RegularEditorForNullPolicyComponent = (props) => {
  const { isNullPolicy, language, currentPolicy, editorTheme } = props
  return (
    <Grid columns={2}>
      <GridRow>
        <GridColumn>
          <Editor
            key='regular-editor-for-null-policy'
            defaultLanguage={language}
            width='100%'
            height='500px'
            defaultValue={currentPolicy}
            theme={editorTheme}
            alwaysConsumeMouseWheel={false}
          />
        </GridColumn>
        <GridColumn>
          <NullPolicyNotification isNullPolicy={isNullPolicy} />
        </GridColumn>
      </GridRow>
    </Grid>
  )
}
