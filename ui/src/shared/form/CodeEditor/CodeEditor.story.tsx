import React, { useState } from 'react';
import { CodeEditor } from './CodeEditor';

export default {
  title: 'Form/Code Editor/Editor',
  component: CodeEditor
};

export const FullHeight = () => {
  const [value, setValue] = useState<string>('Hello, World!');

  return (
    <div style={{ width: 'calc(100vw - 50px)', height: 'calc(100vh - 50px)' }}>
      <CodeEditor
        value={value}
        language="text"
        height="100%"
        width="100%"
        maxHeight={undefined}
        onChange={v => setValue(v as string)}
      />
    </div>
  );
};

export const Disabled = () => {
  const [value, setValue] = useState<string>('Hello, World!');

  return (
    <div style={{ width: '50vw', height: '300px' }}>
      <CodeEditor
        value={value}
        disabled={true}
        language="text"
        onChange={v => setValue(v as string)}
      />
    </div>
  );
};

export const SchemaValidation = () => {
  const [value, setValue] = useState<string>(
    JSON.stringify(
      {
        p1: 'v3',
        p2: false
      },
      null,
      2
    )
  );

  return (
    <div style={{ width: '50vw', height: '300px' }}>
      <CodeEditor
        schemaUri="http://myserver/foo-schema.json"
        schema={{
          type: 'object',
          properties: {
            p1: {
              enum: ['v1', 'v2']
            },
            p2: {
              type: 'object',
              properties: {
                q1: {
                  enum: ['x1', 'x2']
                }
              }
            }
          }
        }}
        value={value}
        language="json"
        onChange={v => setValue(v as string)}
      />
    </div>
  );
};
