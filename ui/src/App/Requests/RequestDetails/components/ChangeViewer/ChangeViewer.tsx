import { LineBreak } from 'shared/elements/LineBreak';
import { Button } from 'shared/elements/Button';
import { DiffEditor } from 'shared/form/DiffEditor/DiffEditor';
import { Chip } from 'shared/elements/Chip';
import styles from './ChangeViewer.module.css';
import { useMemo, useState } from 'react';
import { RequestFile } from '../../types';

type ChangeViewerProps = {
  file: RequestFile;
  handleModifyChange: (file: RequestFile) => void;
  readOnly?: boolean;
};

const ChangeViewer = ({
  file,
  handleModifyChange,
  readOnly = false
}: ChangeViewerProps) => {
  const [modifiedTemplate, setModifiedTemplate] = useState(file.template_body);

  const hasChanged = useMemo(
    () => modifiedTemplate !== file.template_body,
    [modifiedTemplate, file.template_body]
  );

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        File: {file.file_path} <Chip type="success">{file.additions}+</Chip>
      </div>
      <DiffEditor
        original={file.previous_body || ''}
        modified={modifiedTemplate}
        onChange={(value: string) => setModifiedTemplate(value)}
        readOnly={readOnly}
      />
      <LineBreak size="large" />
      {!readOnly && (
        <>
          <Button
            disabled={!hasChanged}
            onClick={() =>
              handleModifyChange({ ...file, template_body: modifiedTemplate })
            }
            fullWidth
            size="small"
          >
            Modify
          </Button>
          <LineBreak />
        </>
      )}
    </div>
  );
};

export default ChangeViewer;
