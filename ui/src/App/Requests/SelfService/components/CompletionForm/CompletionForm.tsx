import { LineBreak } from 'shared/elements/LineBreak';
import { Button } from 'shared/elements/Button';
import { useCallback, useEffect, useContext, useState } from 'react';
import styles from './CompletionForm.module.css';
import SelfServiceContext from '../../SelfServiceContext';
import { SubmittableRequest, TemplatePreview } from '../../types';
import axios from 'core/Axios/Axios';
import { DiffEditor } from 'shared/form/DiffEditor';
import { Spinner } from 'shared/elements/Spinner';
import { Link } from 'react-router-dom';
import { convertToSubmittableRequest } from './utils';
import { Segment } from 'shared/layout/Segment';

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
    <Segment disablePadding isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Request Summary</h3>
        <LineBreak />
        <p className={styles.subText}>Please select a change type</p>
        <LineBreak size="large" />
        <div className={styles.content}>
          <DiffEditor
            original={templateResponse?.current_template_body || ''}
            modified={revisedTemplateBody || ''}
            onChange={onChange}
          />
          <LineBreak size="large" />
          <Button
            size="small"
            color="primary"
            fullWidth
            onClick={handleSubmit}
            disabled={isLoading}
          >
            Submit Request
          </Button>
        </div>
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
    </Segment>
  );
};

export default CompletionForm;
