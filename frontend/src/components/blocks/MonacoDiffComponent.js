import React, { useEffect, useRef, useState } from 'react'
import { DiffEditor, useMonaco } from '@monaco-editor/react'
import PropTypes from 'prop-types'
import {
  getMonacoTriggerCharacters,
  getMonacoCompletions,
  getStringFormat,
  getLocalStorageSettings,
  convertToCloudFormation,
  convertToTerraform,
} from '../../helpers/utils'
import { Menu } from 'semantic-ui-react'

const MonacoDiffComponent = (props) => {
  const monaco = useMonaco()
  const onLintError = props.onLintError
  const onValueChange = props.onValueChange
  const renderSideBySide =
    typeof props.renderSideBySide !== 'undefined'
      ? props.renderSideBySide
      : true
  const modifiedEditorRef = useRef()
  const [language, setLanguage] = useState('json')
  const [languageDetected, setLanguageDetected] = useState(false)
  const [activeItem, setActiveItem] = useState('JSON')

  const onChange = (newValue) => {
    onValueChange(newValue)
  }

  useEffect(() => {
    if (!monaco) return
    monaco.languages.registerCompletionItemProvider('json', {
      triggerCharacters: getMonacoTriggerCharacters(),
      async provideCompletionItems(model, position) {
        return await getMonacoCompletions(model, position, monaco)
      },
    })
  }, [monaco])

  useEffect(
    () => {
      const { newValue } = props
      if (!newValue || languageDetected) return
      setLanguage(getStringFormat(newValue))
      setLanguageDetected(true)
    },
    [props.newValue] // eslint-disable-line
  )

  const editorDidMount = (editor, monaco) => {
    editor._modifiedEditor.onDidChangeModelContent((_) => {
      onChange(editor._modifiedEditor.getValue())
    })
    editor._modifiedEditor.onDidChangeModelDecorations(() => {
      if (modifiedEditorRef.current) {
        const model = modifiedEditorRef.current.getModel()
        if (model === null || model.getModeId() !== 'json') {
          return
        }

        const owner = model.getModeId()
        const uri = model.uri
        const markers = monaco.editor.getModelMarkers({ owner, resource: uri })
        onLintError(
          markers.map(
            (marker) =>
              `Lint error on line ${marker.startLineNumber} columns
              ${marker.startColumn}-${marker.endColumn}: ${marker.message}`
          )
        )
      }
    })
    modifiedEditorRef.current = editor._modifiedEditor
  }

  const { oldValue, newValue, readOnly } = props
  const options = {
    selectOnLineNumbers: true,
    renderSideBySide: renderSideBySide,
    enableSplitViewResizing: false,
    quickSuggestions: true,
    scrollbar: {
      alwaysConsumeMouseWheel: false,
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
    readOnly,
  }
  const readOnlyOptions = { ...options, readOnly: true }
  const editorTheme = getLocalStorageSettings('editorTheme')
  if (props.showIac) {
    return (
      <div>
        <Menu pointing secondary>
          <Menu.Item
            name='JSON'
            content='JSON'
            active={activeItem === 'JSON'}
            onClick={() => {
              setActiveItem('JSON')
            }}
          ></Menu.Item>
          <Menu.Item
            name='Terraform'
            content='Terraform'
            active={activeItem === 'Terraform'}
            onClick={() => {
              setActiveItem('Terraform')
            }}
          ></Menu.Item>
          <Menu.Item
            name='CloudFormation'
            content='CloudFormation'
            active={activeItem === 'CloudFormation'}
            onClick={() => {
              setActiveItem('CloudFormation')
            }}
          ></Menu.Item>
        </Menu>
        {activeItem === 'JSON' ? (
          <DiffEditor
            language={language}
            width='100%'
            height='500px'
            original={oldValue}
            modified={newValue}
            onMount={editorDidMount}
            options={options}
            onChange={onChange}
            theme={editorTheme}
            alwaysConsumeMouseWheel={false}
          />
        ) : null}
        {activeItem === 'Terraform' ? (
          <DiffEditor
            language={'hcl'}
            width='100%'
            height='500px'
            original={oldValue}
            modified={convertToTerraform(
              props?.policyName || 'policyName',
              newValue,
              props.principal
            )}
            onMount={editorDidMount}
            options={readOnlyOptions}
            theme={editorTheme}
            alwaysConsumeMouseWheel={false}
          />
        ) : null}
        {activeItem === 'CloudFormation' ? (
          <DiffEditor
            language={'yaml'}
            width='100%'
            height='500px'
            original={oldValue}
            modified={convertToCloudFormation(
              props?.policyName || 'policyName',
              newValue,
              props.principal
            )}
            onMount={editorDidMount}
            options={readOnlyOptions}
            theme={editorTheme}
            alwaysConsumeMouseWheel={false}
          />
        ) : null}
      </div>
    )
  } else {
    return (
      <DiffEditor
        language={language}
        width='100%'
        height='500px'
        original={oldValue}
        modified={newValue}
        onMount={editorDidMount}
        options={options}
        onChange={onChange}
        theme={editorTheme}
        alwaysConsumeMouseWheel={false}
      />
    )
  }
}

// This component requires four props:
// 1. oldValue = old value for the diff
// 2. newValue = new value for the diff
// 3. readOnly = whether the new value should be readOnly or not
// 4. onLintError = method that will be called whenever a lint error is detected
// 5. onChange = method that will be called whenever a chance occurs to upate the value

MonacoDiffComponent.propTypes = {
  oldValue: PropTypes.string.isRequired,
  newValue: PropTypes.string.isRequired,
  readOnly: PropTypes.bool.isRequired,
  onLintError: PropTypes.func.isRequired,
  onValueChange: PropTypes.func.isRequired,
}
export default MonacoDiffComponent
