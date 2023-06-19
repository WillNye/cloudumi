import { useCallback, useMemo, useState } from 'react';
import { DEFAULT_REQUEST, SELF_SERVICE_STEPS } from './constants';
import RequestViewer from './components/RequestViewer';
import SelfServiceContext from './SelfServiceContext';
import { Button } from 'shared/elements/Button';

import styles from './SelfService.module.css';
import {
  ChangeType,
  ChangeTypeDetails,
  IRequest,
  Identity,
  RequestType
} from './types';

const SelfService = () => {
  const [currentStep, setCurrentStep] = useState(
    SELF_SERVICE_STEPS.SELECT_PROVIDER
  );
  const [selfServiceRequest, setSelfServiceRequest] =
    useState<IRequest>(DEFAULT_REQUEST);

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

  const handleNext = useCallback(() => {
    console.log('handleNext', currentStep);
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
        setSelectedProvider('');
        setCurrentStep(SELF_SERVICE_STEPS.SELECT_PROVIDER);
        break;
      case SELF_SERVICE_STEPS.REQUEST_TYPE:
        setSelectedIdentityType('');
        setCurrentStep(SELF_SERVICE_STEPS.SELECT_IDENTITY);
        break;
      case SELF_SERVICE_STEPS.CHANGE_TYPE:
        setSelectedRequestType(null);
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
          selfServiceRequest
        },
        actions: {
          setCurrentStep,
          setSelectedProvider,
          setSelectedIdentityType,
          setSelectedIdentity,
          setSelectedRequestType,
          // setSelectedChangeType,
          addChange,
          removeChange
        }
      }}
    >
      <div className={styles.container}>
        <div className={styles.content}>
          <div className={styles.wrapper}>
            <RequestViewer />
          </div>
          <div className={styles.actions}>
            {canClickBack && (
              <Button size="small" onClick={handleBack}>
                Back
              </Button>
            )}
            {canClickNext && currentStep === SELF_SERVICE_STEPS.CHANGE_TYPE && (
              <Button
                size="small"
                disabled={!selfServiceRequest.requestedChanges.length}
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
      </div>
    </SelfServiceContext.Provider>
  );
};

export default SelfService;
