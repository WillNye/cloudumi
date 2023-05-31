import { useState } from 'react';
import { SELF_SERICE_STEPS } from './constants';
import RequestViewier from './components/RequestViewier';
import SelfServiceContext from './SelfServiceContext';

const SelfService = () => {
  const [currentStep, setCurrentStep] = useState(
    SELF_SERICE_STEPS.SELECT_PROVIDER
  );

  return (
    <SelfServiceContext.Provider
      value={{
        store: {
          currentStep
        },
        actions: {
          setCurrentStep
        }
      }}
    >
      <RequestViewier />
    </SelfServiceContext.Provider>
  );
};

export default SelfService;
