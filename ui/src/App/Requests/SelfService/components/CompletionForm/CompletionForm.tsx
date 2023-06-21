import { LineBreak } from 'shared/elements/LineBreak';
import { Button } from 'shared/elements/Button';
import { useCallback, useEffect, useContext, useState } from 'react';
import styles from './CompletionForm.module.css';
import SelfServiceContext from '../../SelfServiceContext';
import { IRequest, SubmittableRequest, TemplatePreview } from '../../types';
import axios from 'core/Axios/Axios';
import { DiffEditor } from 'shared/form/DiffEditor';
import { Spinner } from 'shared/elements/Spinner';
import { Link } from 'react-router-dom';

function convertToSubmittableRequest(request: IRequest): SubmittableRequest {
  const changes = request.requestedChanges.map(change => {
    const fields = change.fields.map(field => ({
      field_key: field.field_key,
      field_value: field.value
    }));

    const providerDefinitionIds = change.included_providers.map(
      provider => provider.id
    );

    return {
      change_type_id: change.id,
      // The provider_definition_ids are unclear from the request, for now returning an empty array
      provider_definition_ids: providerDefinitionIds,
      fields: fields
    };
  });

  return {
    iambic_template_id: request.identity?.id || '',
    file_path: null,
    justification: request.justification || '',
    template_body: null,
    template: null,
    expires_at: request.expirationDate || '',
    changes: changes
  };
}

const CompletionForm = () => {
  const [submittableRequest, setSubmittableRequest] =
    useState<SubmittableRequest | null>(null);
  const [templateResponse, setTemplateResponse] =
    useState<TemplatePreview | null>(null);
  const [revisedTemplateBody, setRevisedTemplateBody] = useState<string | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [responseContent, setResponseContent] = useState<any>(null);

  const {
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

  useEffect(() => {
    if (selfServiceRequest) {
      setIsLoading(true);
      const convertedRequest = convertToSubmittableRequest(selfServiceRequest);
      setSubmittableRequest(convertedRequest);

      axios
        .post('/api/v4/self-service/requests/validate', convertedRequest)
        .then(response => {
          setTemplateResponse(response?.data?.data);
        })
        .catch(error => {
          console.error(error);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [selfServiceRequest]);

  useEffect(() => {
    if (templateResponse) {
      setRevisedTemplateBody(templateResponse?.request_data?.template_body);
    }
  }, [templateResponse]);

  const onChange = (value: string) => {
    setRevisedTemplateBody(value);
  };

  const handleSubmit = useCallback(() => {
    if (revisedTemplateBody && submittableRequest) {
      setIsLoading(true);
      const payload = {
        iambic_template_id: submittableRequest.iambic_template_id,
        justification: submittableRequest.justification,
        template_body: revisedTemplateBody
      };

      axios
        .post('/api/v4/self-service/requests', payload)
        .then(response => {
          setResponseContent(response.data);
        })
        .catch(error => {
          console.error(error);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [revisedTemplateBody, submittableRequest]);

  return (
    <div className={styles.container}>
      <h3>Request Summary</h3>
      <LineBreak />
      {isLoading ? (
        <Spinner />
      ) : (
        <>
          <DiffEditor
            original={templateResponse?.current_template_body || ''}
            modified={revisedTemplateBody || ''}
            onChange={onChange}
          />
          <div className={styles.content}>
            <LineBreak size="large" />
            <Button
              size="small"
              color="primary"
              fullWidth
              onClick={handleSubmit}
            >
              Submit Request
            </Button>
          </div>
        </>
      )}
      {responseContent?.data?.request_id && (
        <div>
          <p>
            Request successfully submitted. Click on the link below to view it
          </p>
          <Link to={`/request/${responseContent?.data?.request_id}`}>
            View Request
          </Link>
        </div>
      )}
    </div>
  );
};

export default CompletionForm;
