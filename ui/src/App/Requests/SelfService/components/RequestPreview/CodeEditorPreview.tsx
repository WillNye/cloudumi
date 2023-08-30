import { LineBreak } from 'shared/elements/LineBreak';
import { DiffEditor } from 'shared/form/DiffEditor';
import { Segment } from 'shared/layout/Segment';

export const CodeEditorPreview = ({
  templateResponse,
  revisedTemplateBody,
  onChange
}) => {
  return (
    <Segment>
      <LineBreak size="large" />
      <DiffEditor
        original={templateResponse?.current_template_body || ''}
        modified={revisedTemplateBody || ''}
        onChange={onChange}
      />
    </Segment>
  );
};

export default CodeEditorPreview;
