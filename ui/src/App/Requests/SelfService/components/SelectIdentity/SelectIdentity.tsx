import { useState, useContext, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Segment } from 'shared/layout/Segment';
import { Select, SelectOption } from 'shared/form/Select';
import SelfServiceContext from '../../SelfServiceContext';
import styles from './SelectIdentity.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { TypeaheadBlock } from 'shared/form/TypeaheadBlock';
import { getRequestTemplateTypes } from 'core/API/iambicRequest';

const SelectIdentity = () => {
  const [typeaheadDefaults, setTypeaheadDefaults] = useState({
    defaultValue: '',
    defaultValues: []
  });
  const { selfServiceRequest } = useContext(SelfServiceContext).store;
  const {
    actions: { setSelectedIdentity, setSelectedIdentityType }
  } = useContext(SelfServiceContext);

  const [typeaheadEndpoint, setTypeaheadEndpoint] = useState(
    selfServiceRequest?.identityType
      ? `/api/v4/templates?template_type=${selfServiceRequest?.identityType}`
      : ''
  );

  const { data: identityTypes, isLoading } = useQuery({
    queryFn: getRequestTemplateTypes,
    queryKey: ['getRequestTemplateTypes', selfServiceRequest.provider]
  });

  const handleIdentityTypeSelect = useCallback(
    identityType => {
      setSelectedIdentityType(identityType);
      setSelectedIdentity(null);
      setTypeaheadEndpoint(`/api/v4/templates?template_type=${identityType}`);
      setTypeaheadDefaults({ defaultValue: '', defaultValues: [] });
    },
    [setSelectedIdentity, setSelectedIdentityType]
  );

  const handleTypeaheadSelect = identity => {
    setSelectedIdentity(identity);
  };

  console.log(selfServiceRequest);
  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Select Identity Type</h3>
        <LineBreak />
        <p className={styles.subText}>Please select an identity type</p>
        <LineBreak size="large" />
        <div className={styles.content}>
          {identityTypes?.data && (
            <Select
              value={selfServiceRequest.identityType || ''}
              onChange={handleIdentityTypeSelect}
              placeholder="Select identity type"
            >
              {identityTypes?.data.map(identityType => (
                <SelectOption key={identityType.id} value={identityType.id}>
                  {identityType.name}
                </SelectOption>
              ))}
            </Select>
          )}
          {selfServiceRequest.identityType && (
            <>
              <LineBreak size="large" />
              <TypeaheadBlock
                defaultValue={
                  selfServiceRequest.identity?.resource_id ||
                  typeaheadDefaults.defaultValue
                }
                defaultValues={typeaheadDefaults.defaultValues}
                handleOnSelectResult={handleTypeaheadSelect}
                resultsFormatter={result => {
                  return <p>{result.resource_id}</p>;
                }}
                endpoint={typeaheadEndpoint}
                queryParam={'resource_id'}
                titleKey={'resource_id'}
              />
            </>
          )}
        </div>
      </div>
    </Segment>
  );
};

export default SelectIdentity;
