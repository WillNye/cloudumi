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

// eslint-disable-next-line complexity
const SelfService = () => {
  const [stepsStack, setStepsStack] = useState([
    SELF_SERVICE_STEPS.SELECT_PROVIDER
  ]);
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

  const resetChanges = () => {
    setSelfServiceRequest(prev => {
      const newRequest = { ...prev, requestedChanges: [] };
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
      currentStep === SELF_SERVICE_STEPS.SELECT_IDENTITY ||
      currentStep === SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES ||
      currentStep === SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS,
    [currentStep]
  );

  const showFooter = useMemo(
    () => canClickNext || canClickBack,
    [canClickNext, canClickBack]
  );

  const wrapperClasses = useMemo(
    () =>
      classNames(styles.wrapper, {
        [styles.fullWidth]: [
          SELF_SERVICE_STEPS.COMPLETION_FORM,
          // SELF_SERVICE_STEPS.SELECT_IDENTITY,
          // SELF_SERVICE_STEPS.CHANGE_TYPE,
          SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES
        ].includes(currentStep)
      }),
    [currentStep]
  );

  const handleNext = useCallback(() => {
    let nextStep = SELF_SERVICE_STEPS.SELECT_PROVIDER;
    if (currentStep === SELF_SERVICE_STEPS.SELECT_PROVIDER) {
      nextStep = SELF_SERVICE_STEPS.REQUEST_TYPE;
    } else if (currentStep === SELF_SERVICE_STEPS.REQUEST_TYPE) {
      nextStep = SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES;
    } else if (currentStep === SELF_SERVICE_STEPS.CHANGE_TYPE) {
      nextStep = SELF_SERVICE_STEPS.COMPLETION_FORM;
    } else if (currentStep === SELF_SERVICE_STEPS.SELECT_IDENTITY) {
      nextStep = SELF_SERVICE_STEPS.CHANGE_TYPE;
    } else if (currentStep === SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES) {
      nextStep = SELF_SERVICE_STEPS.SELECT_IDENTITY;
    } else if (currentStep === SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS) {
      nextStep = SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES;
    }
    setStepsStack(stack => [...stack, nextStep]);
    setCurrentStep(nextStep);
  }, [currentStep]);

  const handleBack = useCallback(() => {
    let newStack = [...stepsStack];
    newStack.pop();
    let lastStep = newStack[newStack.length - 1];
    setStepsStack(newStack);
    setCurrentStep(lastStep);

    // switch (currentStep) {
    //   case SELF_SERVICE_STEPS.SELECT_IDENTITY:
    //     setSelectedIdentityType('');
    //     setSelectedIdentity(null);
    //     setCurrentStep(SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES);
    //     break;
    //   case SELF_SERVICE_STEPS.REQUEST_TYPE:
    //     setSelectedRequestType(null);
    //     setCurrentStep(SELF_SERVICE_STEPS.SELECT_PROVIDER);
    //     break;
    //   case SELF_SERVICE_STEPS.CHANGE_TYPE:
    //     setCurrentStep(SELF_SERVICE_STEPS.REQUEST_TYPE);
    //     break;
    //   case SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES:
    //     setCurrentStep(SELF_SERVICE_STEPS.REQUEST_TYPE);
    //     break;
    //   case SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS:
    //     setCurrentStep(SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES);
    //     break;
    //   case SELF_SERVICE_STEPS.COMPLETION_FORM:
    //     // setSelectedChangeType(null);
    //     setCurrentStep(SELF_SERVICE_STEPS.CHANGE_TYPE);
    //     break;
    //   // case SELF_SERVICE_STEPS.COMPLETION_FORM:
    //   //   setSelectedChangeType(null);
    //   //   setCurrentStep(SELF_SERVICE_STEPS.CHANGE_TYPE);
    //   //   break;
    //   default:
    //     break;
    // }
  }, [stepsStack]);

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
          resetChanges,
          setExpirationType,
          setRelativeValue,
          setRelativeUnit,
          setDateValue,
          setTimeValue,
          setExpirationDate,
          handleNext
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
              {canClickNext &&
                currentStep === SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES && (
                  <Button
                    size="small"
                    disabled={!selfServiceRequest.requestedChanges.length}
                    onClick={handleNext}
                  >
                    Next
                  </Button>
                )}
              {canClickNext &&
                currentStep === SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS && (
                  <Button
                    size="small"
                    disabled={!selfServiceRequest.identity}
                    onClick={handleNext}
                  >
                    Next
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
