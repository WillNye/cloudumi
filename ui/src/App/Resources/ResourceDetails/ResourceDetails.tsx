import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Uri } from 'monaco-editor';
import { setDiagnosticsOptions } from 'monaco-yaml';
import schema from './aws_iam_role_template.json';
import { JSONSchema7 } from 'json-schema';
import { CodeEditor } from 'shared/form/CodeEditor';
import { Button } from 'shared/elements/Button';
import styles from './ResourceDetails.module.css';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';
import { LineBreak } from 'shared/elements/LineBreak';
import { useQuery } from '@tanstack/react-query';
import { getResource } from 'core/API/resources';
import { NotFound } from 'App/NotFound/NotFound';
import { Loader } from 'shared/elements/Loader';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';

const configureYAMLSchema = async (
  editorInstance: any,
  monaco: any,
  content: string
) => {
  const modelUri = Uri.parse('inmemory://model/main.yaml');
  // const monaco = editorInstance.getModel().getMode()._worker(monaco);
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
  monaco.editor.createModel(content, 'yaml', modelUri);
};

const ResourcesDetails = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isModified, setIsModified] = useState<boolean>(false);

  const { provider, '*': fullPath } = useParams<{
    provider: string;
    '*': string;
  }>();

  const { data, isLoading } = useQuery({
    queryFn: getResource,
    queryKey: ['getResource', `${provider}/${fullPath}`],
    onError: (error: AxiosError) => {
      const errorRes = error?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(errorMsg || 'An error occurred fetching resource');
    }
  });

  const handleEditorChange = (value: string) => {
    setIsModified(value !== data?.raw_template_yaml);
  };

  if (isLoading) {
    return <Loader />;
  }

  if (errorMessage) {
    return <NotFound />;
  }

  return (
    <div className={styles.container}>
      <div className={styles.pageHeader}>
        <h3>Resources</h3>
        <LineBreak />
        <Breadcrumbs
          items={[
            { name: 'Resources', url: '/resources' },
            { name: `${provider}/${fullPath}`, url: `/${provider}/${fullPath}` }
          ]}
        />
      </div>

      <div className={styles.details}>
        <table className={styles.table}>
          <tbody>
            <tr>
              <td>Template Type</td>
              <td>{data?.template_type}</td>
            </tr>
            <tr>
              <td>Identifier</td>
              <td>{data?.identifier}</td>
            </tr>
            <tr>
              <td>Description</td>
              <td>{data?.description}</td>
            </tr>
            <tr>
              <td>File path</td>
              <td>{data?.file_path}</td>
            </tr>
            <tr>
              <td>External Link</td>
              <td>
                <Link to={data?.external_link} target="_blank">
                  Click here
                </Link>
              </td>
            </tr>
            <tr>
              <td>Last Updated</td>
              <td>{new Date(data?.last_updated).toUTCString()}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className={styles.section}>
        <h4 className={styles.sidebar}>Resource History</h4>
        <div className={styles.content}>
          <div className={styles.editor}>
            <CodeEditor
              height="100%"
              defaultLanguage="yaml"
              value={data?.raw_template_yaml}
              onChange={handleEditorChange}
              onMount={(editor, monaco) =>
                configureYAMLSchema(editor, monaco, data?.raw_template_yaml)
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
