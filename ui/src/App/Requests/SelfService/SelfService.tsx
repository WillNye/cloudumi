import { useCallback, useMemo, useState } from 'react';
import { SELF_SERICE_STEPS } from './constants';
import RequestViewer from './components/RequestViewer';
import SelfServiceContext from './SelfServiceContext';
import { Button } from 'shared/elements/Button';

import styles from './SelfService.module.css';
import { ChangeType, ChangeTypeDetails, RequestType } from './types';

const SelfService = () => {
  const [currentStep, setCurrentStep] = useState(
    SELF_SERICE_STEPS.SELECT_PROVIDER
  );
  const [selfServiceRequest, setSelfServiceRequest] = useState();
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedRequestType, setSelectedRequestType] =
    useState<RequestType | null>(null);
  const [selectedChangeType, setSelectedChangeType] =
    useState<ChangeType | null>(null);
  const [requestedChanges, setRequestedChanges] = useState<ChangeTypeDetails[]>(
    []
  );

  const addChange = (change: ChangeTypeDetails) => {
    setRequestedChanges(prev => [...prev, change]);
  };

  const removeChange = index => {
    setRequestedChanges(prev => prev.filter((_, i) => i !== index));
  };

  const canClickBack = useMemo(
    () => currentStep !== SELF_SERICE_STEPS.SELECT_PROVIDER,
    [currentStep]
  );

  const canClickNext = useMemo(
    () => currentStep === SELF_SERICE_STEPS.CHANGE_TYPE,
    [currentStep]
  );

  const handleNext = useCallback(() => {
    setCurrentStep(SELF_SERICE_STEPS.COMPLETION_FORM);
  }, []);

  const handleBack = useCallback(() => {
    switch (currentStep) {
      case SELF_SERICE_STEPS.REQUEST_TYPE:
        setSelectedProvider('');
        setCurrentStep(SELF_SERICE_STEPS.SELECT_PROVIDER);
        break;
      case SELF_SERICE_STEPS.CHANGE_TYPE:
        setSelectedRequestType(null);
        setCurrentStep(SELF_SERICE_STEPS.REQUEST_TYPE);
        break;
      case SELF_SERICE_STEPS.COMPLETION_FORM:
        setSelectedChangeType(null);
        setCurrentStep(SELF_SERICE_STEPS.CHANGE_TYPE);
        break;
      // case SELF_SERICE_STEPS.COMPLETION_FORM:
      //   setSelectedChangeType(null);
      //   setCurrentStep(SELF_SERICE_STEPS.CHANGE_TYPE);
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
          selectedProvider,
          selectedRequestType,
          selectedChangeType,
          requestedChanges
        },
        actions: {
          setCurrentStep,
          setSelectedProvider,
          setSelectedRequestType,
          setSelectedChangeType,
          addChange,
          removeChange
        }
      }}
    >
      <div className={styles.container}>
        <div className={styles.content}>
          <RequestViewer />
          <div className={styles.actions}>
            {canClickBack && (
              <Button size="small" onClick={handleBack}>
                Back
              </Button>
            )}
            {canClickNext && (
              <Button
                size="small"
                // color="secondary"
                // variant="outline"
                disabled={!selectedChangeType}
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
