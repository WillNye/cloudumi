import { LineBreak } from 'shared/elements/LineBreak';
import { useEffect, useContext, useState } from 'react';
import styles from './RequestPreview.module.css';
import SelfServiceContext from '../../SelfServiceContext';
import { TemplatePreview } from '../../types';
import axios from 'core/Axios/Axios';
import { convertToSubmittableRequest } from './utils';
import { Segment } from 'shared/layout/Segment';
import { extractErrorMessage } from 'core/API/utils';
import errorImg from '../../../../../assets/illustrations/empty.svg';
import Tabs from 'shared/elements/Tabs';
import CodeEditorPreview from './CodeEditorPreview';
import RequestSummary from './RequestSummary';

const RequestPreview = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [templateResponse, setTemplateResponse] =
    useState<TemplatePreview | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const {
    store: { selfServiceRequest, revisedTemplateBody },
    actions: { setSubmittableRequest, setRevisedTemplateBody }
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
          const errorMessage = extractErrorMessage(error?.response);
          setErrorMessage(
            errorMessage || 'Error while validating selected changes'
          );
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
    return () => {
      setSubmittableRequest(null);
    };
  }, [selfServiceRequest, setSubmittableRequest]);

  useEffect(() => {
    if (templateResponse) {
      setRevisedTemplateBody(templateResponse?.request_data?.template_body);
    }
    return () => {
      setRevisedTemplateBody(null);
    };
  }, [setRevisedTemplateBody, templateResponse]);

  const onChange = (value: string) => {
    setRevisedTemplateBody(value);
  };

  return (
    <Segment disablePadding isLoading={isLoading} className={styles.wrapper}>
      <div className={styles.container}>
        <h3>Request Summary</h3>
        <LineBreak />
        <p className={styles.subText}>
          This is a summary of the pull request that will be generated after you
          hit Submit.
        </p>
        <LineBreak />
        {errorMessage ? (
          <div className={styles.notificationAlert}>
            <LineBreak size="large" />
            <img src={errorImg} />
            <LineBreak size="large" />
            <h5>Invalid Request</h5>
            <p className={styles.text}>{errorMessage}</p>
          </div>
        ) : (
          <Tabs
            tabs={[
              {
                label: 'Summary',
                content: <RequestSummary />
              },
              {
                label: 'Code Editor',
                content: (
                  <CodeEditorPreview
                    templateResponse={templateResponse}
                    revisedTemplateBody={revisedTemplateBody}
                    onChange={onChange}
                  />
                )
              }
            ]}
          />
        )}
      </div>
    </Segment>
  );
};

export default RequestPreview;
