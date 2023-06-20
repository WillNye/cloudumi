import { LineBreak } from 'shared/elements/LineBreak';
import { Button } from 'shared/elements/Button';
import { useCallback, useEffect, useContext, useState } from 'react';
import styles from './CompletionForm.module.css';
import SelfServiceContext from '../../SelfServiceContext';
import { Dialog } from 'shared/layers/Dialog';
import { IRequest, SubmittableRequest, TemplatePreview } from '../../types';
import axios from 'core/Axios/Axios';
import { DiffEditor } from 'shared/form/DiffEditor';

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

  const {
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

  useEffect(() => {
    if (selfServiceRequest) {
      const convertedRequest = convertToSubmittableRequest(selfServiceRequest);
      setSubmittableRequest(convertedRequest);

      axios
        .post('/api/v4/self-service/requests/validate', convertedRequest)
        .then(response => {
          setTemplateResponse(response?.data?.data);
        })
        .catch(error => {
          console.error(error);
        });
    }
  }, [selfServiceRequest]);

  useEffect(() => {
    if (templateResponse) {
      setRevisedTemplateBody(templateResponse?.request_data?.template_body);
    }
  }, [templateResponse]);

  const handleSubmit = useCallback(() => {
    if (revisedTemplateBody && submittableRequest) {
      const payload = {
        iambic_template_id: submittableRequest.iambic_template_id,
        justification: submittableRequest.justification,
        template_body: revisedTemplateBody
      };

      axios
        .post('/api/v4/self-service/requests', payload)
        .then(response => {
          console.log(response.data);
        })
        .catch(error => {
          console.error(error);
        });
    }
  }, [revisedTemplateBody, submittableRequest]);

  return (
    <div className={styles.container}>
      <h3>Request Summary</h3>
      <LineBreak />
      <DiffEditor
        original={templateResponse?.current_template_body || ''}
        modified={revisedTemplateBody || ''}
      />
      <div className={styles.content}>
        <LineBreak size="large" />
        <Button size="small" color="primary" fullWidth onClick={handleSubmit}>
          Submit Request
        </Button>
      </div>
    </div>
  );
};

export default CompletionForm;
