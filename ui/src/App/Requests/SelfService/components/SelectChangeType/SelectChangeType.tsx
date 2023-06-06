import { useEffect, useState } from 'react';
import axios from 'core/Axios/Axios';
import { Segment } from 'shared/layout/Segment';
import styles from './SelectChangeType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext, {
  ChangeType as ChangeTypeContext
} from '../../SelfServiceContext';
import { SELF_SERICE_STEPS } from '../../constants';
import { Select } from '@noqdev/cloudscape';
import { Button } from 'shared/elements/Button';
import { Dialog } from 'shared/layers/Dialog';
import RequestChangeDetails from '../RequestChangeDetails';

interface ChangeType {
  id: string;
  name: string;
  description: string;
  request_type_id: string;
}

interface ApiResponse {
  status_code: number;
  data: ChangeType[];
}

const SelectChangeType = () => {
  const [changeTypes, setChangeTypes] = useState<ChangeType[]>([]);
  const [showModal, setShowModal] = useState(false);
  const { selectedRequestType, selectedChangeType } =
    useContext(SelfServiceContext).store;

  const {
    actions: { setCurrentStep, setSelectedChangeType }
  } = useContext(SelfServiceContext);

  useEffect(() => {
    if (selectedRequestType) {
      const fetchData = async () => {
        const result = await axios.get<ApiResponse>(
          `/api/v4/self-service/request-types/${selectedRequestType.id}/change-types/`
        );
        setChangeTypes(result.data.data);
      };

      fetchData();
    }
  }, [selectedRequestType]);

  const handleSelectChange = (detail: any) => {
    const selectedChange = changeTypes.find(
      changeType => changeType.id === detail.value
    );
    setSelectedChangeType(selectedChange as ChangeTypeContext);
    // Do something with the selected option
  };

  const options = changeTypes.map(changeType => ({
    label: changeType.name,
    value: changeType.id,
    description: changeType.description
  }));

  return (
    <Segment>
      <div className={styles.container}>
        <h3>Select Change Type</h3>
        <LineBreak />
        <p className={styles.subText}>Please select a change type</p>
        <LineBreak size="large" />
        <label>
          Change Type:
          <Select
            selectedOption={
              selectedChangeType && {
                label: selectedChangeType.name,
                value: selectedChangeType.id,
                description: selectedChangeType.description
              }
            }
            onChange={({ detail }) => handleSelectChange(detail.selectedOption)}
            options={options}
            filteringType="auto"
            selectedAriaLabel="Selected"
          />
        </label>
        <LineBreak size="large" />

        {/* <Dialog setShowDialog={setShowModal} showDialog={showModal}> */}
        {selectedChangeType && <RequestChangeDetails />}

        {/* </Dialog> */}
      </div>
    </Segment>
  );
};

export default SelectChangeType;
