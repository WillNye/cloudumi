import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Segment } from 'shared/layout/Segment';
import { Checkbox } from 'shared/form/Checkbox';
import { Button } from 'shared/elements/Button';
import styles from './EULA.module.css';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { acceptEndUserAgreement, getEndUserAgreement } from 'core/API/auth';
import { Tooltip } from 'shared/elements/Tooltip';
import { Block } from 'shared/layout/Block';
import { extractErrorMessage } from 'core/API/utils';
import { useAuth } from 'core/Auth';
import { useMutation, useQuery } from '@tanstack/react-query';
import { LineBreak } from 'shared/elements/LineBreak';

const SCROLL_HEIGHT_OFFSET = 5;

const EULA = () => {
  const ref = useRef();

  const [isLoading, setIsLoading] = useState(true);
  const [agreementDocument, setAgreementDocument] = useState('');
  const [hasViewedAgreement, setHasViewedAgreement] = useState(false);
  const [acceptAgreement, setAcceptAgreement] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [fetchError, setFetchError] = useState(null);

  const { user, getUser } = useAuth();
  const navigate = useNavigate();

  useQuery({
    queryFn: getEndUserAgreement,
    queryKey: ['getEula'],
    onSettled: () => {
      setIsLoading(false);
    },
    onSuccess: ({ data }) => {
      if (data?.eula) {
        setAgreementDocument(data.eula);
      } else {
        const errorMessage = extractErrorMessage(data);
        setFetchError(errorMessage);
      }
    },
    onError: error => {
      const errorMessage = extractErrorMessage(error);
      setFetchError(errorMessage);
    }
  });

  const { mutateAsync: acceptEndUserAgreementMutation } = useMutation({
    mutationFn: acceptEndUserAgreement,
    mutationKey: ['acceptEndUserAgreement']
  });

  const handleOnChange = event => {
    setAcceptAgreement(() => event.target.checked);
  };

  const handleOnSubmit = useCallback(() => {
    setIsLoading(true);
    acceptEndUserAgreementMutation()
      .then(async () => {
        await getUser();
        navigate('/');
      })
      .catch(error => {
        if (error?.response?.status === 400) {
          navigate('/');
        } else {
          const errorMessage = extractErrorMessage(error);
          setSubmitError(errorMessage);
        }
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [navigate, getUser, acceptEndUserAgreementMutation]);

  const onScroll = useCallback(() => {
    if (ref.current) {
      const { scrollTop, scrollHeight, clientHeight } = ref.current;
      const height = scrollTop + clientHeight;
      if (height + SCROLL_HEIGHT_OFFSET >= scrollHeight) {
        setHasViewedAgreement(true);
      }
    }
  }, [ref]);

  if (!user?.needs_to_sign_eula) {
    return <Navigate to="/" />;
  }

  return (
    <div className={styles.eula}>
      {fetchError ? (
        <Segment>
          <div>
            <h1>An error occured</h1>
            <p>We are already informed, please try again later</p>
            <LineBreak />
            <Link to="/">
              <Button color="primary">Return to Home</Button>
            </Link>
          </div>
        </Segment>
      ) : (
        <Segment isLoading={isLoading}>
          <div className={styles.container}>
            <h3>Terms of Service</h3>
            <Segment>
              <textarea
                onScroll={onScroll}
                ref={ref}
                className={styles.document}
                readOnly
                value={agreementDocument}
                data-cy="eula-textarea"
              ></textarea>
            </Segment>

            {/* <Divider horizontal /> */}

            {submitError && (
              <Notification
                type={NotificationType.ERROR}
                header="Error"
                fullWidth
                data-cy="submit-error-notification"
              >
                {submitError}
              </Notification>
            )}

            <div className={styles.actions}>
              <p>
                By clicking below, you agree to the Noq Terms and Conditons of
                Service and Privacy Policy.
              </p>
            </div>

            {/* <Divider horizontal /> */}

            <div className={styles.actions}>
              <Tooltip
                text="Read the EULA to continue (scroll to the bottom)"
                disabled={hasViewedAgreement}
              >
                <div className={styles.accept}>
                  <Block>Accept</Block>
                  <Checkbox
                    onChange={handleOnChange}
                    checked={acceptAgreement}
                    disabled={!hasViewedAgreement}
                    data-cy="accept-eula-checkbox"
                  />
                </div>
              </Tooltip>
            </div>

            <LineBreak />

            <div className={styles.actions}>
              <Button
                className={styles.button}
                color="primary"
                fullWidth
                disabled={!acceptAgreement}
                onClick={handleOnSubmit}
                data-cy="continue-button"
              >
                Continue
              </Button>
            </div>
          </div>
        </Segment>
      )}
    </div>
  );
};

export default EULA;
