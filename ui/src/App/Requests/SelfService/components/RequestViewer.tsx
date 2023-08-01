import { useContext } from 'react';
import SelfServiceContext from '../SelfServiceContext';
import { Segment } from 'shared/layout/Segment';
import { SELF_SERVICE_STEPS } from '../constants';
import SelectIdentity from './AdvancedFlow/SelectIdentity';
import SelectProvider from './SelectProvider';
import SelectRequestType from './SelectRequestType';
import SelectChangeType from './AdvancedFlow/SelectChangeType';
import RequestPreview from './RequestPreview';
import ExpressChangeType from './ExpressFlow/ExpressChangeType';
import ExpressChangeDetails from './ExpressFlow/ExpressChangeDetails';

export const STEP_COMPONENTS = {
  [SELF_SERVICE_STEPS.SELECT_PROVIDER]: SelectProvider,
  [SELF_SERVICE_STEPS.REQUEST_TYPE]: SelectRequestType,
  [SELF_SERVICE_STEPS.EXPRESS_CHANGE_TYPES]: ExpressChangeType,
  [SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS]: ExpressChangeDetails,
  [SELF_SERVICE_STEPS.SELECT_IDENTITY]: SelectIdentity,
  [SELF_SERVICE_STEPS.CHANGE_TYPE]: SelectChangeType,
  [SELF_SERVICE_STEPS.COMPLETION_FORM]: RequestPreview
};

const RequestViewer = () => {
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

export default RequestViewer;
