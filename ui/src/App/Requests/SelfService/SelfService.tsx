import { useCallback, useMemo, useState } from 'react';
import {
  DEFAULT_REQUEST,
  EXPIRATION_TYPE,
  SELF_SERVICE_STEPS
} from './constants';
import RequestViewer from './components/RequestViewer';
import SelfServiceContext from './SelfServiceContext';
import { Button } from 'shared/elements/Button';

import styles from './SelfService.module.css';
import { ChangeTypeDetails, IRequest, Identity, RequestType } from './types';
import { Divider } from 'shared/elements/Divider';
import { DateTime } from 'luxon';
import classNames from 'classnames';

const SelfService = () => {
  const [currentStep, setCurrentStep] = useState(
    SELF_SERVICE_STEPS.SELECT_PROVIDER
  );
  const [expirationType, setExpirationType] = useState(EXPIRATION_TYPE.NEVER);
  const [relativeValue, setRelativeValue] = useState('4');
  const [relativeUnit, setRelativeUnit] = useState('hours');
  const [dateValue, setDateValue] = useState(
    DateTime.fromJSDate(new Date()).toFormat('yyyy-MM-dd')
  );
  const [timeValue, setTimeValue] = useState('00:00:00');
  const [selfServiceRequest, setSelfServiceRequest] =
    useState<IRequest>(DEFAULT_REQUEST);

  const setJustification = (justification: string) => {
    setSelfServiceRequest(prev => {
      const newRequest = { ...prev, justification };
      return newRequest;
    });
  };

  const setSelectedProvider = (provider: string) => {
    setSelfServiceRequest(prev => {
      const newRequest = { ...prev, provider };
      return newRequest;
    });
  };

  const setSelectedIdentityType = (identityType: string) => {
    setSelfServiceRequest(prev => {
      const newRequest = { ...prev, identityType };
      return newRequest;
    });
  };

  const setSelectedIdentity = (identity: Identity) => {
    setSelfServiceRequest(prev => {
      const newRequest = { ...prev, identity };
      return newRequest;
    });
  };

  const setSelectedRequestType = (requestType: RequestType) => {
    setSelfServiceRequest(prev => {
      const newRequest = { ...prev, requestType };
      return newRequest;
    });
  };

  const addChange = (change: ChangeTypeDetails) => {
    setSelfServiceRequest(prev => {
      const requestedChanges = [...prev.requestedChanges, change];
      const newRequest = { ...prev, requestedChanges };
      return newRequest;
    });
  };

  const setExpirationDate = (date: string | null) => {
    setSelfServiceRequest(prev => ({ ...prev, expirationDate: date }));
  };

  const removeChange = index => {
    setSelfServiceRequest(prev => {
      const requestedChanges = prev.requestedChanges.filter(
        (_, i) => i !== index
      );
      const newRequest = { ...prev, requestedChanges };
      return newRequest;
    });
  };

  const canClickBack = useMemo(
    () => currentStep !== SELF_SERVICE_STEPS.SELECT_PROVIDER,
    [currentStep]
  );

  const canClickNext = useMemo(
    () =>
      currentStep === SELF_SERVICE_STEPS.CHANGE_TYPE ||
      currentStep === SELF_SERVICE_STEPS.SELECT_IDENTITY,
    [currentStep]
  );

  const showFooter = useMemo(
    () => canClickNext || canClickBack,
    [canClickNext, canClickBack]
  );

  const wrapperClasses = useMemo(
    () =>
      classNames(styles.wrapper, {
        [styles.fullWidth]: currentStep === SELF_SERVICE_STEPS.COMPLETION_FORM
      }),
    [currentStep]
  );

  const handleNext = useCallback(() => {
    if (currentStep === SELF_SERVICE_STEPS.CHANGE_TYPE) {
      setCurrentStep(SELF_SERVICE_STEPS.COMPLETION_FORM);
    } else if (currentStep === SELF_SERVICE_STEPS.SELECT_IDENTITY) {
      setCurrentStep(SELF_SERVICE_STEPS.REQUEST_TYPE);
    }
  }, [currentStep]);

  const handleBack = useCallback(() => {
    switch (currentStep) {
      case SELF_SERVICE_STEPS.SELECT_IDENTITY:
        setSelectedIdentityType('');
        setSelectedIdentity(null);
        setCurrentStep(SELF_SERVICE_STEPS.SELECT_PROVIDER);
        break;
      case SELF_SERVICE_STEPS.REQUEST_TYPE:
        setSelectedRequestType(null);
        setCurrentStep(SELF_SERVICE_STEPS.SELECT_IDENTITY);
        break;
      case SELF_SERVICE_STEPS.CHANGE_TYPE:
        setCurrentStep(SELF_SERVICE_STEPS.REQUEST_TYPE);
        break;
      case SELF_SERVICE_STEPS.COMPLETION_FORM:
        // setSelectedChangeType(null);
        setCurrentStep(SELF_SERVICE_STEPS.CHANGE_TYPE);
        break;
      // case SELF_SERVICE_STEPS.COMPLETION_FORM:
      //   setSelectedChangeType(null);
      //   setCurrentStep(SELF_SERVICE_STEPS.CHANGE_TYPE);
      //   break;
      default:
        break;
    }
  }, [currentStep]);

  return (
    <SelfServiceContext.Provider
      value={{
        store: {
          currentStep,
          selfServiceRequest,
          expirationType,
          relativeValue,
          relativeUnit,
          dateValue,
          timeValue
        },
        actions: {
          setCurrentStep,
          setSelectedProvider,
          setSelectedIdentityType,
          setSelectedIdentity,
          setSelectedRequestType,
          setJustification,
          setSelfServiceRequest,
          addChange,
          removeChange,
          setExpirationType,
          setRelativeValue,
          setRelativeUnit,
          setDateValue,
          setTimeValue,
          setExpirationDate
        }
      }}
    >
      <div className={styles.container}>
        <div className={styles.content}>
          <div className={wrapperClasses}>
            <RequestViewer />
          </div>
        </div>
        {showFooter && (
          <div className={styles.actionsWrapper}>
            <Divider />
            <div className={styles.actions}>
              {canClickBack && (
                <Button size="small" onClick={handleBack}>
                  Back
                </Button>
              )}
              {canClickNext && currentStep === SELF_SERVICE_STEPS.CHANGE_TYPE && (
                <Button
                  size="small"
                  disabled={
                    !(
                      selfServiceRequest.requestedChanges.length &&
                      selfServiceRequest.justification
                    )
                  }
                  onClick={handleNext}
                >
                  Next
                </Button>
              )}
              {canClickNext &&
                currentStep === SELF_SERVICE_STEPS.SELECT_IDENTITY && (
                  <Button
                    size="small"
                    disabled={!selfServiceRequest.identity}
                    onClick={handleNext}
                  >
                    Next
                  </Button>
                )}
            </div>
          </div>
        )}
      </div>
    </SelfServiceContext.Provider>
  );
};

export default SelfService;
