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
  CreateIambicRequest,
  IRequest,
  Identity,
  RequestType,
  SubmittableRequest
} from './types';
import { Divider } from 'shared/elements/Divider';
import { DateTime } from 'luxon';
import classNames from 'classnames';
import SidePanel from './components/SidePanel';
import { useMutation } from '@tanstack/react-query';
import { createIambicRequest } from 'core/API/iambicRequest';
import { Link, useNavigate } from 'react-router-dom';
import { Icon } from 'shared/elements/Icon';
import { Segment } from 'shared/layout/Segment';
import { LineBreak } from 'shared/elements/LineBreak';

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
  const [submittableRequest, setSubmittableRequest] =
    useState<SubmittableRequest | null>(null);
  const [revisedTemplateBody, setRevisedTemplateBody] = useState<string | null>(
    null
  );
  const [createdRequest, setCreatedRequest] = useState(null);

  const navigate = useNavigate();

  const {
    mutateAsync: createIambicRequestMutation,
    isLoading: isRequestSubmitting
  } = useMutation({
    mutationFn: (payload: CreateIambicRequest) => createIambicRequest(payload),
    mutationKey: ['createIambicRequest']
  });

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

  const showFooter = useMemo(() => {
    if (createdRequest?.request_id) {
      return false;
    }
    return canClickNext || canClickBack;
  }, [canClickNext, canClickBack, createdRequest]);

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

  const handleSubmit = useCallback(async () => {
    if (revisedTemplateBody && submittableRequest) {
      const payload = {
        iambic_template_id: submittableRequest.iambic_template_id,
        justification: submittableRequest.justification,
        template_body: revisedTemplateBody
      };
      try {
        const data = await createIambicRequestMutation(payload);
        console.log(data);
        setCreatedRequest(data?.data);
      } catch (error) {
        console.error(error);
      }
    }
  }, [createIambicRequestMutation, revisedTemplateBody, submittableRequest]);

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
          timeValue,
          revisedTemplateBody,
          submittableRequest
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
          handleNext,
          setSubmittableRequest,
          setRevisedTemplateBody
        }
      }}
    >
      <div className={styles.container}>
        <div className={styles.content}>
          <div className={wrapperClasses}>
            <Segment isLoading={isRequestSubmitting}>
              {createdRequest?.request_id ? (
                <div className={styles.notificationAlert}>
                  <div>
                    <Icon name="notification-success" size="large" />
                    <LineBreak size="small" />
                    <p className={styles.text}>
                      Request successfully submitted. Click on the link below to
                      view it
                    </p>
                    <LineBreak size="small" />
                    <Link to={`/requests/${createdRequest.request_id}`}>
                      View Request
                    </Link>
                  </div>
                </div>
              ) : (
                <RequestViewer />
              )}
            </Segment>
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
              <div>
                <Button
                  size="small"
                  variant="outline"
                  onClick={() => navigate('/requests')}
                >
                  Cancel
                </Button>
                {currentStep === SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES && (
                  <Button
                    size="small"
                    disabled={!selfServiceRequest.changeType}
                    onClick={() => handleNext()}
                  >
                    Next
                  </Button>
                )}
                {currentStep === SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS && (
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
                {currentStep === SELF_SERVICE_STEPS.REQUEST_PREVIEW && (
                  <Button
                    size="small"
                    disabled={
                      !revisedTemplateBody ||
                      !submittableRequest ||
                      isRequestSubmitting
                    }
                    onClick={handleSubmit}
                  >
                    Submit Request
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </SelfServiceContext.Provider>
  );
};

export default SelfService;
