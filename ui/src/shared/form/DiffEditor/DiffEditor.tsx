import { FC, useEffect, useState } from 'react';
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
  readOnly?: boolean;
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
  readOnly = false,
  onChange
}) => {
  const [renderSideBySide, setRenderSideBySide] = useState(false);
  const monaco = useMonaco();

  const options = {
    ...DEFAULT_EDITOR_OPTIONS,
    renderSideBySide,
    readOnly
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
  }, [monaco, language]);

  const editorDidMount = (editor, monaco) => {
    const modifiedEditor = editor.getModifiedEditor();
    modifiedEditor.onDidChangeModelContent(_ => {
      onChange && onChange(modifiedEditor.getValue());
    });

    // Create diff navigator and move to the first difference
    const diffNavigator = monaco.editor.createDiffNavigator(editor, {
      followsCaret: true,
      ignoreCharChanges: true
    });
    diffNavigator.next();
  };

  return (
    <div className={styles.editorBlock}>
      <div className={styles.renderStyle}>
        <Button
          onClick={() => setRenderSideBySide(false)}
          icon="column"
          color={renderSideBySide ? 'secondary' : 'primary'}
          size="small"
        />
        <Button
          onClick={() => setRenderSideBySide(true)}
          icon="columns"
          color={renderSideBySide ? 'primary' : 'secondary'}
          size="small"
        />
      </div>

      {modified && (
        <MonacoDiffEditor
          language={language}
          width="100%"
          height="500px"
          original={original}
          modified={modified}
          options={options}
          theme="vs-dark"
          onMount={editorDidMount}
          className={styles.editor}
        />
      )}
    </div>
  );
};
