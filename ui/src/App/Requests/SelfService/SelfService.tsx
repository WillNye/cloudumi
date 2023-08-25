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
import SidePanel from './components/SidePanel';

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

  const setExpressTemplateId = useCallback(template_id => {
    setSelfServiceRequest(prev => ({
      ...prev,
      express_template_id: template_id
    }));
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
      [
        SELF_SERVICE_STEPS.CHANGE_TYPE,
        SELF_SERVICE_STEPS.SELECT_IDENTITY,
        SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES,
        SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS
      ].includes(currentStep),
    [currentStep]
  );

  const showFooter = useMemo(
    () => canClickNext || canClickBack,
    [canClickNext, canClickBack]
  );

  const hideSidePanel = useMemo(
    () =>
      [
        SELF_SERVICE_STEPS.SELECT_PROVIDER,
        SELF_SERVICE_STEPS.REQUEST_PREVIEW
      ].includes(currentStep),
    [currentStep]
  );

  const wrapperClasses = useMemo(
    () =>
      classNames(styles.wrapper, {
        [styles.defaultWidth]: [SELF_SERVICE_STEPS.SELECT_PROVIDER].includes(
          currentStep
        )
      }),
    [currentStep]
  );

  const handleNext = useCallback(
    (newMode?: REQUEST_FLOW_MODE) => {
      const mode = newMode || currentMode;
      const stepMapper =
        mode === REQUEST_FLOW_MODE.EXPRESS_MODE
          ? EXPRESS_MODE_NEXT_STEP_MAP
          : ADVANCED_MODE_NEXT_STEP_MAP;
      const newCurrentStep = stepMapper[currentStep];
      setCurrentStep(newCurrentStep);

      if (newMode) {
        setCurrentMode(newMode);
      }
    },
    [currentStep, currentMode]
  );

  const handleBack = useCallback(() => {
    const stepMapper =
      currentMode === REQUEST_FLOW_MODE.EXPRESS_MODE
        ? EXPRESS_MODE_PREVIOUS_STEP_MAP
        : ADVANCED_MODE_PREVIOUS_STEP_MAP;
    const newCurrentStep = stepMapper[currentStep];
    setCurrentStep(newCurrentStep);

    if (newCurrentStep === SELF_SERVICE_STEPS.SELECT_PROVIDER) {
      setSelfServiceRequest(DEFAULT_REQUEST);
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
          setExpressTemplateId,
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
            {!hideSidePanel && <SidePanel />}
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
              {canClickNext && (
                <>
                  {currentStep === SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES && (
                    <Button
                      size="small"
                      disabled={!selfServiceRequest.changeType}
                      onClick={() => handleNext()}
                    >
                      Next
                    </Button>
                  )}
                  {currentStep ===
                    SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS && (
                    <Button
                      size="small"
                      disabled={!selfServiceRequest.requestedChanges}
                      onClick={() => handleNext()}
                    >
                      Next
                    </Button>
                  )}
                  {currentStep === SELF_SERVICE_STEPS.CHANGE_TYPE && (
                    <Button
                      size="small"
                      disabled={
                        !(
                          selfServiceRequest.requestedChanges.length &&
                          selfServiceRequest.justification
                        )
                      }
                      onClick={() => handleNext()}
                    >
                      Next
                    </Button>
                  )}
                  {currentStep === SELF_SERVICE_STEPS.SELECT_IDENTITY && (
                    <Button
                      size="small"
                      disabled={!selfServiceRequest.identity}
                      onClick={() => handleNext()}
                    >
                      Next
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </SelfServiceContext.Provider>
  );
};

export default SelfService;
