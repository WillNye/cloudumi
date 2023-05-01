import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { mockData } from './mockData';
// Replace this with the actual API function to fetch the template details
// import { getTemplateDetails } from 'core/API/resources';
import { Uri } from 'monaco-editor';
import { setDiagnosticsOptions } from 'monaco-yaml';
import schema from './aws_iam_role_template.json';
import { JSONSchema7 } from 'json-schema';
import { CodeEditor } from 'shared/form/CodeEditor';
import { Button } from 'shared/elements/Button';
import styles from './ResourceDetails.module.css';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';
import { LineBreak } from 'shared/elements/LineBreak';

const configureYAMLSchema = async (
  editorInstance: any,
  monaco: any,
  content: string
) => {
  const modelUri = Uri.parse('inmemory://model/main.yaml');
  //const monaco = editorInstance.getModel().getMode()._worker(monaco);
  console.log(editorInstance);
  console.log(monaco);

  setDiagnosticsOptions({
    enableSchemaRequest: true,
    hover: true,
    completion: true,
    validate: true,
    format: true,
    schemas: [
      {
        uri: 'https://docs.iambic.org/schemas/v1/aws_iam_role_template.json',
        fileMatch: [String(modelUri)],
        schema: schema as JSONSchema7
      }
    ]
  });
  const model = monaco.editor.createModel(content, 'yaml', modelUri);
  editorInstance.setModel(model);
  // monaco.editor.createModel(content, 'yaml', modelUri);
};

const ResourcesDetails = () => {
  const { provider, '*': fullPath } = useParams<{
    provider: string;
    '*': string;
  }>();
  const [orgName, repoName, ...filePathParts] = fullPath.split('/');
  const fullRepoName = `${orgName}/${repoName}`;
  const filePath = filePathParts.join('/') + '.yaml';
  const [templateContent, setTemplateContent] = useState<string>('');
  const [isModified, setIsModified] = useState<boolean>(false);

  async function getTemplateDetails(repoName: string, filePath: string) {
    // TODO: Implement this function to fetch the template details
    return { data: { file_content: '123' } }; // Return an empty object for now
  }

  async function fetchTemplateDetails() {
    try {
      const response = await getTemplateDetails(repoName, filePath);
      setTemplateContent(response.data.file_content);
    } catch (error) {
      console.error('Error fetching template details:', error);
    }
  }

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      // Use the resourceId to find the corresponding mock resource
      const mockResource = mockData.find(
        resource => resource.file_path === filePath
      );

      // If the mock resource is found, set the content to the file_contents property
      if (mockResource) {
        setTemplateContent(mockResource.file_contents);
      } else {
        console.error(`Resource with identifier "${filePath}" not found.`);
      }
    } else {
      fetchTemplateDetails();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filePath]);

  const handleEditorChange = (value: string) => {
    setIsModified(value !== templateContent);
  };

  return (
    <div className={styles.container}>
      <div className={styles.pageHeader}>
        <h3>Resources</h3>
        <LineBreak />
        <Breadcrumbs
          items={[
            { name: 'Resources', url: '/resources' },
            { name: 'template_name', url: '/resources' }
          ]}
        />
      </div>

      <div className={styles.section}>
        <div className={styles.sidebar}>Resource</div>
        <div className={styles.content}>
          <div className={styles.editor}>
            <CodeEditor
              defaultLanguage="yaml"
              value={templateContent}
              onChange={handleEditorChange}
              onMount={(editor, monaco) =>
                configureYAMLSchema(editor, monaco, templateContent)
              }
            />
          </div>
          <LineBreak />
          <Button
            onClick={() => alert('Submitting request')}
            disabled={!isModified}
            size="small"
          >
            Submit Request
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ResourcesDetails;
