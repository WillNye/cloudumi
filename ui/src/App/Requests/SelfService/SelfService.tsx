import { useCallback, useMemo, useState } from 'react';
import {
  ADVANCED_MODE_NEXT_STEP_MAP,
  ADVANCED_MODE_PREVIOUS_STEP_MAP,
  DEFAULT_REQUEST,
  EXPIRATION_TYPE,
  EXPRESS_MODE_NEXT_STEP_MAP,
  EXPRESS_MODE_PREVIOUS_STEP_MAP,
  REQUEST_FLOW_MODE,
  SELF_SERVICE_STEPS
} from './constants';
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
import { Divider } from 'shared/elements/Divider';
import { DateTime } from 'luxon';
import classNames from 'classnames';

const SelfService = () => {
  const [currentStep, setCurrentStep] = useState(
    SELF_SERVICE_STEPS.SELECT_PROVIDER
  );
  const [currentMode, setCurrentMode] = useState(
    REQUEST_FLOW_MODE.EXPRESS_MODE
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

  const setJustification = useCallback((justification: string) => {
    setSelfServiceRequest(prev => ({ ...prev, justification }));
  }, []);

  const setSelectedProvider = useCallback((provider: string) => {
    setSelfServiceRequest(prev => ({ ...prev, provider }));
  }, []);

  const setSelectedIdentityType = useCallback((identityType: string) => {
    setSelfServiceRequest(prev => ({ ...prev, identityType }));
  }, []);

  const setSelectedIdentity = useCallback((identity: Identity) => {
    setSelfServiceRequest(prev => ({ ...prev, identity }));
  }, []);

  const setSelectedRequestType = useCallback((requestType: RequestType) => {
    setSelfServiceRequest(prev => ({ ...prev, requestType }));
  }, []);

  const addChange = useCallback((change: ChangeTypeDetails) => {
    setSelfServiceRequest(prev => {
      const requestedChanges = [...prev.requestedChanges, change];
      const newRequest = { ...prev, requestedChanges };
      return newRequest;
    });
  }, []);

  const addChangeType = useCallback((changeType: ChangeType) => {
    setSelfServiceRequest(prev => ({ ...prev, changeType }));
  }, []);

  const resetChanges = useCallback(() => {
    setSelfServiceRequest(prev => ({ ...prev, requestedChanges: [] }));
  }, []);

  const setExpirationDate = useCallback((date: string | null) => {
    setSelfServiceRequest(prev => ({ ...prev, expirationDate: date }));
  }, []);

  const removeChange = useCallback(index => {
    setSelfServiceRequest(prev => {
      const requestedChanges = prev.requestedChanges.filter(
        (_, i) => i !== index
      );
      const newRequest = { ...prev, requestedChanges };
      return newRequest;
    });
  }, []);

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
          SELF_SERVICE_STEPS.REQUEST_PREVIEW,
          // SELF_SERVICE_STEPS.SELECT_IDENTITY,
          // SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS,
          SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES
        ].includes(currentStep)
      }),
    [currentStep]
  );

  console.log(selfServiceRequest, '++++++++++++++testing------------');

  const handleNext = useCallback(() => {
    if (currentMode === REQUEST_FLOW_MODE.EXPRESS_MODE) {
      setCurrentStep(EXPRESS_MODE_NEXT_STEP_MAP[currentStep]);
    } else {
      setCurrentStep(ADVANCED_MODE_NEXT_STEP_MAP[currentStep]);
    }
  }, [currentStep, currentMode]);

  const handleBack = useCallback(() => {
    if (currentMode === REQUEST_FLOW_MODE.EXPRESS_MODE) {
      setCurrentStep(EXPRESS_MODE_PREVIOUS_STEP_MAP[currentStep]);
    } else {
      setCurrentStep(ADVANCED_MODE_PREVIOUS_STEP_MAP[currentStep]);
    }
  }, [currentMode, currentStep]);

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
          addChangeType,
          removeChange,
          resetChanges,
          setExpirationType,
          setRelativeValue,
          setRelativeUnit,
          setDateValue,
          setTimeValue,
          setCurrentMode,
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
                    // disabled={!selfServiceRequest.changeType}
                    disabled={!selfServiceRequest.identityType}
                    onClick={handleNext}
                  >
                    Next
                  </Button>
                )}
              {canClickNext &&
                currentStep === SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS && (
                  <Button
                    size="small"
                    disabled={!selfServiceRequest.requestedChanges}
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
