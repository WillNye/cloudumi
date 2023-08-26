import { useCallback, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Uri } from 'monaco-editor';
import { setDiagnosticsOptions } from 'monaco-yaml';
import schema from './aws_iam_role_template.json';
import { JSONSchema7 } from 'json-schema';
import { CodeEditor } from 'shared/form/CodeEditor';
import { Button } from 'shared/elements/Button';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';
import { LineBreak } from 'shared/elements/LineBreak';
import { useMutation, useQuery } from '@tanstack/react-query';
import { getResource } from 'core/API/resources';
import { NotFound } from 'App/NotFound/NotFound';
import { Loader } from 'shared/elements/Loader';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { Dialog } from 'shared/layers/Dialog';
import { Block } from 'shared/layout/Block';
import { Segment } from 'shared/layout/Segment';
import { Divider } from 'shared/elements/Divider';

import styles from './ResourceDetails.module.css';
import { TextArea } from 'shared/form/TextArea';
import { createIambicRequest } from 'core/API/iambicRequest';

type UpdateResourceparams = {
  justification: string;
  template_body: string;
  file_path?: string;
};

const configureYAMLSchema = async (
  editorInstance: any,
  monaco: any,
  content: string
) => {
  const modelUri = Uri.parse('inmemory://model/main.yaml');
  // const monaco = editorInstance.getModel().getMode()._worker(monaco);

  const schemaUri = Uri.parse(
    'https://docs.iambic.org/schemas/v1/aws_iam_role_template.json'
  );

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

const ResourceDetails = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [createdRequest, setCreatedRequest] = useState(null);
  const [modifiedTemplate, setModifiedTemplate] = useState<string | null>(null);
  const [justification, setJustification] = useState('');
  const [showDialog, setShowDialog] = useState(false);

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

  const isTemplateModified = useMemo(() => {
    if (!modifiedTemplate || !data?.raw_template_yaml) {
      return false;
    }
    return modifiedTemplate !== data?.raw_template_yaml;
  }, [data, modifiedTemplate]);

  const { mutateAsync: updateResourceMutation, isLoading: isSubmitting } =
    useMutation({
      mutationFn: (payload: UpdateResourceparams) =>
        createIambicRequest(payload),
      mutationKey: ['createIambicRequest'],
      onSettled: () => setJustification('')
    });

  const handleOnUpdate = useCallback(async () => {
    setSubmitError(null);
    setCreatedRequest(null);
    setShowDialog(false);
    try {
      const payload = {
        justification,
        template_body: modifiedTemplate,
        file_path: data?.file_path
      };
      const response = await updateResourceMutation(payload);
      setCreatedRequest(response.data);
    } catch (err) {
      const error = err as AxiosError;
      const errorRes = error?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setSubmitError(errorMsg || 'An error occurred while updating resource');
    }
  }, [modifiedTemplate, updateResourceMutation, data, justification]);

  if (isLoading) {
    return <Loader />;
  }

  if (errorMessage) {
    return <NotFound />;
  }

  return (
    <Segment isLoading={isSubmitting}>
      <div className={styles.container}>
        <div className={styles.pageHeader}>
          <h3>Resources</h3>
          <LineBreak />
          <Breadcrumbs
            items={[
              { name: 'Resources', url: '/resources' },
              {
                name: `${provider}/${fullPath}`,
                url: `/${provider}/${fullPath}`
              }
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
              {data?.description && (
                <tr>
                  <td>Description</td>
                  <td>{data?.description}</td>
                </tr>
              )}
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
        {submitError && (
          <>
            <Notification
              header={submitError}
              type={NotificationType.ERROR}
              fullWidth
              onClose={() => setSubmitError(null)}
            />
            <LineBreak />
          </>
        )}
        {createdRequest && (
          <>
            <Notification
              header="Request created"
              type={NotificationType.SUCCESS}
              fullWidth
              onClose={() => setCreatedRequest(null)}
            >
              <p className={styles.text}>
                Click{' '}
                <Link to={`/requests/${createdRequest.request_id}`}>here</Link>{' '}
                to view request
              </p>
            </Notification>
            <LineBreak />
          </>
        )}
        <div className={styles.section}>
          <div className={styles.content}>
            <div className={styles.editor}>
              <CodeEditor
                height="100%"
                defaultLanguage="yaml"
                schemaUri={
                  'https://docs.iambic.org/schemas/v1/aws_iam_role_template.json'
                }
                value={data?.raw_template_yaml}
                onChange={value => setModifiedTemplate(value)}
                onMount={(editor, monaco) =>
                  configureYAMLSchema(editor, monaco, data?.raw_template_yaml)
                }
              />
            </div>
            <LineBreak />
            <Button
              onClick={() => setShowDialog(true)}
              disabled={!isTemplateModified || isSubmitting}
              size="small"
            >
              Submit Request
            </Button>
          </div>
        </div>

        <Dialog
          header="Resource"
          size="medium"
          showDialog={showDialog}
          setShowDialog={setShowDialog}
        >
          <Segment>
            <p>
              Enter the a justification of the updating{' '}
              <Link to={data?.external_link}>{data?.file_path}</Link>
            </p>
            <LineBreak />
            <form>
              <Block disableLabelPadding label="Justification" />
              <TextArea
                value={justification}
                onChange={e => setJustification(e.target.value)}
              />
              <LineBreak size="large" />
              <div className={styles.actions}>
                <Button
                  size="small"
                  fullWidth
                  color="secondary"
                  variant="outline"
                  onClick={() => setShowDialog(false)}
                >
                  Cancel
                </Button>
                <Divider orientation="vertical" />
                <Button
                  size="small"
                  fullWidth
                  disabled={!justification}
                  onClick={handleOnUpdate}
                >
                  Submit
                </Button>
              </div>
            </form>
          </Segment>
        </Dialog>
      </div>
    </Segment>
  );
};

export default ResourceDetails;
