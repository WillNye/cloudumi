import { Segment } from 'shared/layout/Segment';
import SelectProvider from './components/SelectProvider';
import SelectRequestType from './components/SelectRequestType';
import { useState } from 'react';
import { SELF_SERICE_STEPS } from './constants';

const SelfService = () => {
  const [currentStep, setCurrentStep] = useState(
    SELF_SERICE_STEPS.SELECT_PROVIDER
  );

  return (
    <Segment>
      {currentStep === SELF_SERICE_STEPS.SELECT_PROVIDER ? (
        // TODO add context provider for selfservice
        <SelectProvider />
      ) : (
        <SelectRequestType />
      )}
    </Segment>
  );
};

export default SelfService;
