import { useCallback, useEffect, useMemo, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './SelectChangeType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../../SelfServiceContext';
import RequestChangeDetails from '../RequestChangeDetails';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getChangeRequestType } from 'core/API/iambicRequest';
import { Block } from 'shared/layout/Block';
import { ChangeType } from '../../../types';
import { Select as CloudScapeSelect } from '@noqdev/cloudscape';
import RequestExpiration from '../../common/RequestExpiration';
import useGetProviderDefinitions from 'App/Requests/SelfService/hooks/useGetProviderDefinitions';

const SelectChangeType = () => {
  const [selectedChangeType, setSelectedChangeType] =
    useState<ChangeType | null>(null);

  const {
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

  const { providerDefinition } = useGetProviderDefinitions({
    provider: selfServiceRequest.provider,
    template_type: selfServiceRequest?.identityType,
    template_id: selfServiceRequest?.identity
      ? selfServiceRequest.identity?.id
      : null
  });

  const selectedRequestType = useMemo(
    () => selfServiceRequest.requestType,
    [selfServiceRequest]
  );

  const { data: changeTypes, isLoading } = useQuery({
    queryKey: [
      'getChangeRequestType',
      selectedRequestType?.id,
      false,
      selfServiceRequest?.identityType
    ],
    queryFn: getChangeRequestType,
    onError: (error: AxiosError) => {
      // Handle the error...
    }
  });

  const handleSelectChange = useCallback(
    (detail: any) => {
      const selectedChange = changeTypes?.data.find(
        changeType => changeType.id === detail.value
      );
      setSelectedChangeType(selectedChange);
      // Do something with the selected option
    },
    [changeTypes?.data]
  );

  const options = useMemo(
    () =>
      changeTypes?.data?.map(changeType => ({
        label: changeType.name,
        value: changeType.id,
        description: changeType.description
      })),
    [changeTypes]
  );

  useEffect(() => {
    if (options?.length === 1) {
      // select default change type when tehre is just one option
      handleSelectChange(options[0]);
    }
  }, [handleSelectChange, options]);

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Select Change Type</h3>
        <LineBreak size="small" />
        <p className={styles.subText}>Please select a change type</p>
        <LineBreak size="large" />
        <div className={styles.content}>
          <LineBreak size="large" />
          <div className={styles.content}>
            <Block disableLabelPadding label="Change Type" />
            <CloudScapeSelect
              selectedOption={
                selectedChangeType && {
                  label: selectedChangeType.name,
                  value: selectedChangeType.id,
                  description: selectedChangeType.description
                }
              }
              onChange={({ detail }) =>
                handleSelectChange(detail.selectedOption)
              }
              options={options}
              filteringType="auto"
              selectedAriaLabel="Selected"
              placeholder="Select change type"
            />
            <LineBreak size="large" />
            {selectedChangeType && (
              <RequestChangeDetails
                selectedChangeType={selectedChangeType}
                providerDefinition={providerDefinition?.data || []}
              />
            )}
            <RequestExpiration />
          </div>
        </div>
      </div>
    </Segment>
  );
};

export default SelectChangeType;
