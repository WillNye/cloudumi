import { useContext } from 'react';
import SelfServiceContext from '../SelfServiceContext';
import { Segment } from 'shared/layout/Segment';
import { SELF_SERICE_STEPS } from '../constants';
import SelectProvider from './SelectProvider';
import SelectRequestType from './SelectRequestType';
import CompletionForm from './CompletionForm';

export const STEP_COMPONENTS = {
  [SELF_SERICE_STEPS.SELECT_PROVIDER]: SelectProvider,
  [SELF_SERICE_STEPS.REQUEST_TYPE]: SelectRequestType,
  [SELF_SERICE_STEPS.COMPLETION_FORM]: CompletionForm
};

const RequestViewier = () => {
  const {
    store: { currentStep }
  } = useContext(SelfServiceContext);
  const ViewerComponent = STEP_COMPONENTS[currentStep];

  return (
    <Segment>
      <ViewerComponent />
    </Segment>
  );
};

export default RequestViewier;
