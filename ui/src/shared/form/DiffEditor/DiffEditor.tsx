import React, { FC, useEffect, useState } from 'react';
import {
  DiffEditor as MonacoDiffEditor,
  useMonaco
} from '@monaco-editor/react';
import './DiffEditor.module.css';
import { Button } from 'shared/elements/Button'; // Update the path according to your Button component
import styles from './DiffEditor.module.css';
import {
  getMonacoCompletions,
  getMonacoTriggerCharacters
} from 'core/utils/monacoUtils';

interface DiffEditorProps {
  original: string;
  modified: string;
  language?: string;
  onChange?: (value: string) => void;
}

const DEFAULT_EDITOR_OPTIONS = {
  selectOnLineNumbers: true,
  renderSideBySide: true,
  enableSplitViewResizing: false,
  quickSuggestions: true,
  scrollbar: {
    alwaysConsumeMouseWheel: false
  },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  readOnly: false
};

export const DiffEditor: FC<DiffEditorProps> = ({
  original,
  modified,
  language = 'yaml',
  onChange
}) => {
  const [renderSideBySide, setRenderSideBySide] = useState(true);
  const monaco = useMonaco();

  const options = {
    ...DEFAULT_EDITOR_OPTIONS,
    renderSideBySide
  };

  const handleSideBySideToggle = () => {
    setRenderSideBySide(!renderSideBySide);
  };

  useEffect(() => {
    if (!monaco) {
      return;
    }
    monaco.languages.registerCompletionItemProvider(language, {
      triggerCharacters: getMonacoTriggerCharacters(),
      async provideCompletionItems(model, position) {
        return await getMonacoCompletions(model, position, monaco);
      }
    });
  }, [monaco]);

  const editorDidMount = (editor, monaco) => {
    const modifiedEditor = editor.getModifiedEditor();
    modifiedEditor.onDidChangeModelContent(_ => {
      onChange && onChange(modifiedEditor.getValue());
    });
  };

  return (
    <div className={styles.editorBlock}>
      <div className={styles.renderStyle}>
        <Button onClick={handleSideBySideToggle}>
          {renderSideBySide ? 'Unified' : 'Side-by-Side'}
        </Button>
      </div>

      <MonacoDiffEditor
        language={language}
        width="100%"
        height="600px"
        original={original}
        modified={modified}
        options={options}
        theme="vs-dark"
        onMount={editorDidMount}
      />
    </div>
  );
};
