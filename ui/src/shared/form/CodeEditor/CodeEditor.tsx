import React, { FC, useCallback, useRef } from 'react';
import Editor, { EditorProps, Monaco } from '@monaco-editor/react';
import { setupEditor } from './instance';
import classNames from 'classnames';
import { useUnmount } from 'react-use';
import css from './CodeEditor.module.css';

interface IDisposable {
  dispose(): void;
}

export interface Suggestion {
  label?: string;
  detail?: string;
  documentation?: string;
}

interface CodeEditorProps extends EditorProps {
  /**
   * Example: http://myserver/foo-schema.json
   */
  schemaUri?: string;
  /**
   * JSON Schema object
   */
  schema?: object;
  disabled?: boolean;
  minHeight?: number;
  maxHeight?: number;
  error?: boolean;
  suggestions?: Suggestion[];
  onBlur?: (event: React.FocusEvent<HTMLDivElement>) => void;
  onFocus?: (event: React.FocusEvent<HTMLDivElement>) => void;
}

const BORDER_PADDING = 5;

export const CodeEditor: FC<CodeEditorProps> = ({
  disabled,
  options,
  suggestions,
  schemaUri,
  schema,
  minHeight = 175,
  maxHeight = 400,
  height = '100%',
  width = '100%',
  error,
  onBlur,
  onFocus,
  ...rest
}) => {
  const elmRef = useRef<HTMLDivElement | null>(null);
  const contentHeightRef = useRef<number>(0);
  const disposables = useRef<IDisposable[]>([]);

  useUnmount(() => disposables.current.forEach(d => d.dispose()));

  const calculateHeight = useCallback(
    (editor: any, height?: number) => {
      if (typeof height === 'undefined') {
        // Retrieve content height directly from the editor if no height provided as param
        height = editor.getContentHeight();
      }

      height = minHeight ? Math.max(minHeight, height as number) : height;
      height = maxHeight ? Math.min(maxHeight, height as number) : height;

      // Ref: https://github.com/nteract/nteract/pull/5587/files
      if (elmRef.current && contentHeightRef.current !== height) {
        elmRef.current.style.height = `calc(${
          height as number
        } + ${BORDER_PADDING}px)`;

        editor.layout({
          width: editor.getLayoutInfo().width,
          height
        });

        contentHeightRef.current = height as number;
      }
    },
    [minHeight, maxHeight]
  );

  const handleEditorWillMount = useCallback(
    (instance: Monaco) => {
      setupEditor(instance);

      // NOTE: This is where you handle custom language/typeaheads
      if (suggestions?.length > 0) {
        const newDisposables = [];

        const completionProvider =
          instance.languages.registerCompletionItemProvider('mylanguage', {
            triggerCharacters: ['.'],
            provideCompletionItems: (_model, _position) => {
              return {
                suggestions: []
              };
            }
          });

        newDisposables.push(completionProvider);

        const hoverProvider = instance.languages.registerHoverProvider(
          'mylanguage',
          {
            provideHover: (_model, _position) => {
              return {
                contents: []
              };
            }
          }
        );

        newDisposables.push(hoverProvider);

        disposables.current = newDisposables;
      }

      // NOTE: This is where you would handle schema validation; eg cloudformation
      if (schemaUri || schema) {
        instance.languages.json.jsonDefaults.setDiagnosticsOptions({
          validate: true,
          schemas: [
            {
              uri: schemaUri,
              fileMatch: ['*'],
              schema
            }
          ]
        });
      }
    },
    [suggestions, schema, schemaUri]
  );

  const onEditorMount = useCallback(
    (editor: any) => {
      calculateHeight(editor);
      editor.onDidContentSizeChange((info: any) => {
        if (info.contentHeightChanged) {
          calculateHeight(editor, info.contentHeight);
        }
      });
    },
    [calculateHeight]
  );

  return (
    <div
      ref={elmRef}
      className={classNames(css.container, 'mousetrap', { [css.error]: error })}
      tabIndex={-1}
      style={{ height, width }}
      onFocus={onFocus}
      onBlur={onBlur}
    >
      <Editor
        {...rest}
        options={{
          readOnly: disabled,
          fontSize: 12,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          ...(options || {}),
          suggest: {
            showWords: false
          },
          minimap: {
            enabled: false
          }
        }}
        theme="noq"
        beforeMount={handleEditorWillMount}
        onMount={onEditorMount}
      />
    </div>
  );
};
