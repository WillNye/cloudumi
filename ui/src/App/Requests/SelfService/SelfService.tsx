import { useState } from 'react';
import { SELF_SERICE_STEPS } from './constants';
import RequestViewer from './components/RequestViewer';
import SelfServiceContext, {
  RequestType,
  ChangeType,
  ChangeTypeDetails
} from './SelfServiceContext';

const SelfService = () => {
  const [currentStep, setCurrentStep] = useState(
    SELF_SERICE_STEPS.SELECT_PROVIDER
  );
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

  const goBack = () => {
    switch (currentStep) {
      case SELF_SERICE_STEPS.REQUEST_TYPE:
        setSelectedProvider('');
        setCurrentStep(SELF_SERICE_STEPS.SELECT_PROVIDER);
        break;
      case SELF_SERICE_STEPS.CHANGE_TYPE:
        setSelectedRequestType(null);
        setCurrentStep(SELF_SERICE_STEPS.REQUEST_TYPE);
        break;
      case SELF_SERICE_STEPS.REQUEST_CHANGE_DETAILS:
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
  };

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
          removeChange,
          goBack
        }
      }}
    >
      <RequestViewer />
    </SelfServiceContext.Provider>
  );
};

export default SelfService;
