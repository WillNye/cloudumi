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

  useEffect(function onMount() {
    getEUla();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleOnChange = event => {
    setAcceptAgreement(() => event.target.checked);
  };

  const getEUla = useCallback(() => {
    setIsLoading(true);
    getEndUserAgreement()
      .then(({ data }) => {
        if (data?.data?.eula) {
          setAgreementDocument(data.data.eula);
        } else {
          const errorMessage = extractErrorMessage(data);
          setFetchError(errorMessage);
        }
      })
      .catch(error => {
        const errorMessage = extractErrorMessage(error);
        setFetchError(errorMessage);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const handleOnSubmit = useCallback(() => {
    setIsLoading(true);
    acceptEndUserAgreement()
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
  }, [navigate, getUser]);

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
            <br />
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
              ></textarea>
            </Segment>

            {/* <Divider horizontal /> */}

            {submitError && (
              <Notification
                type={NotificationType.ERROR}
                header="Error"
                fullWidth
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
                  />
                </div>
              </Tooltip>
            </div>

            <br />

            <div className={styles.actions}>
              <Button
                className={styles.button}
                color="primary"
                fullWidth
                disabled={!acceptAgreement}
                onClick={handleOnSubmit}
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
