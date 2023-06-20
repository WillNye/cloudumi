import React, { FC, useState } from 'react';
import { DiffEditor as MonacoDiffEditor } from '@monaco-editor/react';
import './DiffEditor.module.css';
import { Button } from 'shared/elements/Button'; // Update the path according to your Button component
import styles from './DiffEditor.module.css';

interface DiffEditorProps {
  original: string;
  modified: string;
  language?: string;
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
  language = 'yaml'
}) => {
  const [renderSideBySide, setRenderSideBySide] = useState(true);

  const options = {
    ...DEFAULT_EDITOR_OPTIONS,
    renderSideBySide
  };

  const handleSideBySideToggle = () => {
    setRenderSideBySide(!renderSideBySide);
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
      />
    </div>
  );
};
