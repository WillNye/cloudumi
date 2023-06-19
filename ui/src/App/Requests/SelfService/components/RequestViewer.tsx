import { useContext } from 'react';
import SelfServiceContext from '../SelfServiceContext';
import { Segment } from 'shared/layout/Segment';
import { SELF_SERICE_STEPS } from '../constants';
import SelectIdentity from './SelectIdentity';
import SelectProvider from './SelectProvider';
import SelectRequestType from './SelectRequestType';
import SelectChangeType from './SelectChangeType';
import CompletionForm from './CompletionForm';

export const STEP_COMPONENTS = {
  [SELF_SERICE_STEPS.SELECT_PROVIDER]: SelectProvider,
  [SELF_SERICE_STEPS.SELECT_IDENTITY]: SelectIdentity,
  [SELF_SERICE_STEPS.REQUEST_TYPE]: SelectRequestType,
  [SELF_SERICE_STEPS.CHANGE_TYPE]: SelectChangeType,
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
