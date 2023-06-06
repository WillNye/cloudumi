import { useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './SelectChangeType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { Select } from '@noqdev/cloudscape';
import RequestChangeDetails from '../RequestChangeDetails';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getChangeRequestType } from 'core/API/iambicRequest';
import { Block } from 'shared/layout/Block';
import { ChangeType } from '../../types';

const SelectChangeType = () => {
  const [changeTypes, setChangeTypes] = useState<ChangeType[]>([]);
  const {
    store: { selectedRequestType, selectedChangeType }
  } = useContext(SelfServiceContext);

  const {
    actions: { setSelectedChangeType }
  } = useContext(SelfServiceContext);

  const { data, isLoading } = useQuery({
    queryFn: getChangeRequestType,
    queryKey: ['getChangeRequestType', selectedRequestType.id],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    },
    onSuccess: ({ data }) => {
      setChangeTypes(data);
    }
  });

  const handleSelectChange = (detail: any) => {
    const selectedChange = changeTypes.find(
      changeType => changeType.id === detail.value
    );
    setSelectedChangeType(selectedChange);
    // Do something with the selected option
  };

  const options = changeTypes.map(changeType => ({
    label: changeType.name,
    value: changeType.id,
    description: changeType.description
  }));

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Select Change Type</h3>
        <LineBreak />
        <p className={styles.subText}>Please select a change type</p>
        <LineBreak size="large" />
        <div className={styles.content}>
          <Block disableLabelPadding label="Change Type" />
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
          <LineBreak size="large" />
          {/* TODO: May use a popup dialog for change details */}
          {selectedChangeType && <RequestChangeDetails />}
        </div>
      </div>
    </Segment>
  );
};

export default SelectChangeType;
