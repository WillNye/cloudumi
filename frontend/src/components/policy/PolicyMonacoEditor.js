import React, { useEffect, useState, useRef, useCallback } from 'react'
import { Button, Form, Icon, Message, Segment } from 'semantic-ui-react'
import Editor, { useMonaco } from '@monaco-editor/react'
import {
  getLocalStorageSettings,
  getMonacoCompletions,
  getMonacoTriggerCharacters,
} from '../../helpers/utils'
import { usePolicyContext } from './hooks/PolicyProvider'
import { useAuth } from '../../auth/AuthProviderDefault'
import './PolicyMonacoEditor.scss'

const editorOptions = {
  selectOnLineNumbers: true,
  quickSuggestions: true,
  scrollbar: {
    alwaysConsumeMouseWheel: false,
  },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  wordWrap: 'wordWrapColumn',
  wordWrapColumn: 120,
}

const lintingErrorMapping = {
  MUTE: 'infoError',
  INFO: 'infoError',
  LOW: 'infoError',
  MEDIUM: 'warningError',
  HIGH: 'criticalError',
  CRITICAL: 'criticalError',
}

const CHECK_POLICY_TIMEOUT = 500

const clearEditorDecorations = ({ editor }) => {
  if (
    editor &&
    editor.getModel &&
    editor.getModel() &&
    editor.getModel().getAllDecorations
  ) {
    editor
      .getModel()
      .getAllDecorations()
      .filter((el) =>
        ['criticalError', 'warningError', 'infoError'].includes(
          el.options.className
        )
      )
      .map((el) => el.reset())
  }
}

const AddEditorDecorations = ({ editor, monaco, errors }) => {
  editor.deltaDecorations(
    [],
    errors.map((error) => ({
      range: new monaco.Range(
        (error.location && error.location.line) || 1,
        1,
        (error.location && error.location.line) || 1,
        // Hardcoded has we don't have the endline number
        Number.MAX_VALUE
      ),
      options: {
        isWholeLine: false,
        className: lintingErrorMapping[error.severity] || 'infoError',
        marginClassName: 'warningIcon',
        hoverMessage: {
          value: `[${error.severity}] ${error.title} - ${error.detail} - ${error.description}`,
        },
      },
    }))
  )
}

// Stub lint error callback, will be setup later
let onLintError = () => {}

const editorDidMount = (editor, monaco) => {
  monaco.languages.registerCompletionItemProvider('json', {
    triggerCharacters: getMonacoTriggerCharacters(),
    async provideCompletionItems(model, position) {
      return await getMonacoCompletions(model, position, monaco)
    },
  })
  editor.onDidChangeModelDecorations(() => {
    const model = editor.getModel()
    if (model === null || model.getModeId() !== 'json') {
      return
    }

    const owner = model.getModeId()
    const uri = model.uri
    const markers = monaco.editor.getModelMarkers({ owner, resource: uri })
    onLintError(
      markers.map(
        (marker) =>
          `Lint error on line ${marker.startLineNumber} columns ${marker.startColumn}-${marker.endColumn}: ${marker.message}`
      )
    )
  })
}

export const PolicyMonacoEditor = ({
  context,
  policy,
  updatePolicy,
  deletePolicy,
  enableLinting = true,
  isSaveButtonDisabled = false,
}) => {
  const { user, sendRequestCommon } = useAuth()
  const { setModalWithAdminAutoApprove, setShowExpirationDate } =
    usePolicyContext()
  const editorRef = useRef()
  const monaco = useMonaco()
  const editorTheme = getLocalStorageSettings('editorTheme')
  const timeout = useRef(null)

  const policyDocumentOriginal = JSON.stringify(
    policy.PolicyDocument,
    null,
    '\t'
  )
  const [policyDocument, setPolicyDocument] = useState(policyDocumentOriginal)
  const [error, setError] = useState('')

  const policyCheck = useCallback(
    async (policy) => {
      if (context === 'inline_policy') {
        const errors = await sendRequestCommon(
          policy,
          '/api/v2/policies/check',
          'post'
        )
        if (errors && typeof errors == 'object' && editorRef.current) {
          // Clear all existing decorations otherwise they will add up
          clearEditorDecorations({ editor: editorRef.current })
          if (monaco) {
            AddEditorDecorations({ editor: editorRef.current, monaco, errors })
          }
        }
      }
    },
    [sendRequestCommon, context] // eslint-disable-line react-hooks/exhaustive-deps
  )

  useEffect(() => {
    // Avoid linting errors if disabled
    if (!enableLinting) {
      return false
    }
    timeout.current = setTimeout(() => {
      if (policyDocument.length) {
        policyCheck(policyDocument)
      }
    }, CHECK_POLICY_TIMEOUT)

    return () => {
      clearInterval(timeout.current)
    }
  }, [policyCheck, policyDocument, enableLinting])

  useEffect(() => {
    setPolicyDocument(policyDocumentOriginal)
  }, [policyDocumentOriginal])

  const onEditChange = (value) => {
    setPolicyDocument(value)
  }

  onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      setError(`LintErrors: ${JSON.stringify(lintErrors)}`)
    } else {
      setError('')
    }
  }

  const handlePolicyAdminSave = useCallback(
    () => {
      updatePolicy({
        ...policy,
        PolicyDocument: JSON.parse(policyDocument),
      })
      setModalWithAdminAutoApprove(true)
      setShowExpirationDate(true)
    },
    [policyDocument, policy] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const handlePolicySubmit = useCallback(
    () => {
      updatePolicy({
        ...policy,
        PolicyDocument: JSON.parse(policyDocument),
      })
      setModalWithAdminAutoApprove(false)
      setShowExpirationDate(true)
    },
    [policyDocument, policy] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const handleDelete = () => {
    deletePolicy({
      ...policy,
      PolicyDocument: JSON.parse(policyDocument),
    })
    setModalWithAdminAutoApprove(true)
    setShowExpirationDate(false)
  }

  function handleEditorDidMount(editor, monaco) {
    editorRef.current = editor
    editorDidMount(editor, monaco)
  }

  return (
    <>
      <Message warning attached='top'>
        <Icon name='warning' />
        {error || `You are editing the policy ${policy.PolicyName}.`}
      </Message>
      <Segment
        attached
        style={{
          border: 0,
          padding: 0,
        }}
      >
        <Editor
          height='540px'
          defaultLanguage='json'
          theme={editorTheme}
          value={policyDocument}
          onChange={onEditChange}
          options={editorOptions}
          onMount={handleEditorDidMount}
          textAlign='center'
        />
      </Segment>
      <Button.Group attached='bottom'>
        {user?.authorization?.can_edit_policies ? (
          <>
            <Button
              positive
              icon='save'
              content='Save'
              onClick={handlePolicyAdminSave}
              disabled={
                error ||
                !policyDocument ||
                policyDocumentOriginal === policyDocument ||
                isSaveButtonDisabled
              }
            />
            <Button.Or />
          </>
        ) : null}
        <Button
          primary
          icon='send'
          content='Submit'
          onClick={handlePolicySubmit}
          disabled={
            error ||
            !policyDocument ||
            policyDocumentOriginal === policyDocument
          }
        />
        {
          // Show delete button for inline policies only
          context === 'inline_policy' &&
          user?.authorization?.can_edit_policies ? (
            <>
              <Button.Or />
              <Button
                negative
                icon='remove'
                content='Delete'
                onClick={handleDelete}
              />{' '}
            </>
          ) : null
        }
      </Button.Group>
    </>
  )
}

export const NewPolicyMonacoEditor = ({
  addPolicy,
  setIsNewPolicy,
  isSaveButtonDisabled = false,
}) => {
  const { user, sendRequestCommon } = useAuth()
  const { setModalWithAdminAutoApprove, setShowExpirationDate } =
    usePolicyContext()
  const editorRef = useRef()
  const editorTheme = getLocalStorageSettings('editorTheme')
  const timeout = useRef(null)
  const monaco = useMonaco()

  const [newPolicyName, setNewPolicyName] = useState('')
  const [templateOptions, setTemplateOptions] = useState([
    { key: 'default', text: '', value: '{}' },
  ])
  const [templateDefaultKey, setTemplateDefaultKey] = useState('Default Policy')

  const [policyDocument, setPolicyDocument] = useState('')
  const [error, setError] = useState('')
  const [policyNameError, setpolicyNameError] = useState(false)
  const policyNameRegex = /^[\w+=,.@-]+$/

  const onEditChange = (value) => {
    setPolicyDocument(value)
  }

  const policyCheck = useCallback(
    async (policy) => {
      const errors = await sendRequestCommon(
        policy,
        '/api/v2/policies/check',
        'post'
      )
      if (errors && typeof errors == 'object' && editorRef.current) {
        // Clear all existing decorations otherwise they will add up
        clearEditorDecorations({ editor: editorRef.current })
        if (monaco) {
          AddEditorDecorations({ editor: editorRef.current, monaco, errors })
        }
      }
    },
    [sendRequestCommon] // eslint-disable-line react-hooks/exhaustive-deps
  )

  useEffect(() => {
    timeout.current = setTimeout(() => {
      if (policyDocument.length) {
        policyCheck(policyDocument)
      }
    }, CHECK_POLICY_TIMEOUT)

    return () => {
      clearInterval(timeout.current)
    }
  }, [policyCheck, policyDocument])

  useEffect(() => {
    ;(async () => {
      const data = await sendRequestCommon(
        null,
        '/api/v2/permission_templates/',
        'get'
      )
      if (!data) {
        return
      }
      setTemplateOptions(data.permission_templates)
      setPolicyDocument(
        JSON.stringify(JSON.parse(templateOptions[0].value), null, '\t')
      )
      setTemplateDefaultKey(templateOptions[0].key)
    })()
  }, []) // eslint-disable-line

  onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      setError(`LintErrors: ${JSON.stringify(lintErrors)}`)
    } else {
      setError('')
    }
  }

  const handleChangeNewPolicyName = (e) => {
    const policyName = e.target.value
    if (policyName && !policyNameRegex.test(policyName)) {
      setpolicyNameError(true)
      return
    }
    setpolicyNameError(false)
    setNewPolicyName(policyName)
  }

  const handlePolicyAdminSave = useCallback(
    () => {
      addPolicy({
        PolicyName: newPolicyName,
        PolicyDocument: JSON.parse(policyDocument),
      })
      setModalWithAdminAutoApprove(true)
      setShowExpirationDate(true)
    },
    [newPolicyName, policyDocument] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const handlePolicySubmit = useCallback(
    () => {
      addPolicy({
        PolicyName: newPolicyName,
        PolicyDocument: JSON.parse(policyDocument),
      })
      setModalWithAdminAutoApprove(false)
      setShowExpirationDate(true)
    },
    [newPolicyName, policyDocument] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const onTemplateChange = (e, { value }) => {
    clearTimeout(timeout)
    clearEditorDecorations({ editor: editorRef.current })
    setPolicyDocument(JSON.stringify(JSON.parse(value || ''), null, '\t'))
  }

  function handleEditorDidMount(editor, monaco) {
    editorRef.current = editor
    editorDidMount(editor, monaco)
  }

  return (
    <>
      <Segment attached='top' color='green'>
        <Form>
          <Form.Group widths='equal'>
            <Form.Input
              id='inputNew'
              error={policyNameError}
              label='Policy Name'
              placeholder='(Optional) Enter a Policy Name'
              onChange={handleChangeNewPolicyName}
            />
            <Form.Dropdown
              label='Template'
              placeholder='Choose a template to add.'
              selection
              onChange={onTemplateChange}
              options={templateOptions}
              defaultValue={templateDefaultKey}
            />
          </Form.Group>
        </Form>
      </Segment>
      <Segment
        attached
        style={{
          border: 0,
          padding: 0,
        }}
      >
        <Editor
          height='540px'
          defaultLanguage='json'
          theme={editorTheme}
          value={policyDocument}
          onChange={onEditChange}
          options={editorOptions}
          onMount={handleEditorDidMount}
          textAlign='center'
        />
      </Segment>
      <Button.Group attached='bottom'>
        {user?.authorization?.can_edit_policies ? (
          <>
            <Button
              positive
              icon='save'
              content='Save'
              onClick={handlePolicyAdminSave}
              disabled={
                error ||
                policyNameError ||
                !policyDocument ||
                isSaveButtonDisabled
              }
            />
            <Button.Or />
          </>
        ) : null}
        <Button
          primary
          icon='send'
          content='Submit'
          onClick={handlePolicySubmit}
          disabled={error || policyNameError || !policyDocument}
        />
        <Button.Or />
        <Button
          negative
          icon='remove'
          content='Cancel'
          onClick={() => setIsNewPolicy(false)}
        />
      </Button.Group>
    </>
  )
}

export const ReadOnlyPolicyMonacoEditor = ({
  policy,
  defaultLanguage = 'json',
  json = true,
}) => {
  const readOnlyEditorOptions = {
    ...editorOptions,
    readOnly: true,
    json: json,
    defaultLanguage: defaultLanguage,
  }
  const editorTheme = getLocalStorageSettings('editorTheme')
  let policyValue = policy
  if (json) {
    policyValue = JSON.stringify(policy, null, '\t')
  }
  return (
    <>
      <Segment
        attached
        style={{
          border: 0,
          padding: 0,
        }}
      >
        <Editor
          height='540px'
          defaultLanguage='json'
          theme={editorTheme}
          value={policyValue}
          options={readOnlyEditorOptions}
          onMount={editorDidMount}
          textAlign='center'
        />
      </Segment>
    </>
  )
}

export const BasePolicyMonacoEditor = ({
  policy,
  defaultLanguage = 'json',
  onChange = () => {},
  json = true,
  readOnly = false,
}) => {
  const EditorOptions = {
    ...editorOptions,
    readOnly: readOnly,
    json: json,
    defaultLanguage: defaultLanguage,
  }
  const editorTheme = getLocalStorageSettings('editorTheme')
  let policyValue = policy
  if (json) {
    policyValue = JSON.stringify(policy, null, '\t')
  }
  return (
    <>
      <Segment
        attached
        style={{
          border: 0,
          padding: 0,
        }}
      >
        <Editor
          height='540px'
          defaultLanguage='json'
          theme={editorTheme}
          value={policyValue}
          options={EditorOptions}
          onMount={editorDidMount}
          onChange={onChange}
          textAlign='center'
        />
      </Segment>
    </>
  )
}
