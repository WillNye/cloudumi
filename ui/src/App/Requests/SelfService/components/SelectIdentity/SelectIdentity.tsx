import { useState, useContext, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Segment } from 'shared/layout/Segment';
import { Select, SelectOption } from 'shared/form/Select';
import SelfServiceContext from '../../SelfServiceContext';
import styles from './SelectIdentity.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { TypeaheadBlock } from 'shared/form/TypeaheadBlock';
import { getRequestTemplateTypes } from 'core/API/iambicRequest';

const TEST_IDENTITIES = [
  {
    id: '2080b8cf-af78-4356-bb8a-305ba329f70f',
    resource_id: 'poweruser',
    resource_type: 'IAM Role',
    template_type: 'NOQ::AWS::IAM::Role',
    provider: 'aws',
    // TODO: Display tooltip?
    tooltip: 'Recently accessed',
    notes: 'Context about this identity'
  },
  {
    id: 'fa0a38c7-0654-4ee1-9813-296a8f85addb',
    resource_id: 'NullRole',
    resource_type: 'IAM Role',
    template_type: 'NOQ::AWS::IAM::Role',
    provider: 'aws'
  },
  {
    id: 'b9e4fd21-bf7d-4225-ad40-897c8783e018',
    resource_id: 'IambicTestDeployUser',
    resource_type: 'IAM User',
    template_type: 'NOQ::AWS::IAM::User',
    provider: 'aws'
  },
  {
    id: '69d44d4d-72b8-486e-89ef-43999eadbe58',
    resource_id: 'AWSReadOnlyAccess',
    resource_type: 'Identity Center Permission Set',
    template_type: 'NOQ::AWS::IdentityCenter::PermissionSet',
    provider: 'aws'
  },
  {
    id: '421ab97f-d6ed-4678-ac98-eec3e81caebe',
    resource_id: 'adino',
    resource_type: 'IAM Managed Policy',
    template_type: 'NOQ::AWS::IAM::ManagedPolicy',
    provider: 'aws'
  },
  {
    id: '7d8785fe-1733-460f-a47f-8fbe794326b0',
    resource_id: 'ctaccess',
    resource_type: 'IAM Group',
    template_type: 'NOQ::AWS::IAM::Group',
    provider: 'aws'
  },
  {
    id: '2a582644-4f16-4d72-a660-5834f99d4750',
    resource_id: 'NoqSaasRoleLocalDev',
    resource_type: 'IAM Role',
    template_type: 'NOQ::AWS::IAM::Role',
    provider: 'aws'
  }
];

const SelectIdentity = () => {
  const [typeaheadDefaults, setTypeaheadDefaults] = useState({
    defaultValue: '',
    defaultValues: []
  });
  const [typeaheadEndpoint, setTypeaheadEndpoint] = useState('');
  const { selfServiceRequest } = useContext(SelfServiceContext).store;
  const {
    actions: { setSelectedIdentity, setSelectedIdentityType }
  } = useContext(SelfServiceContext);

  const { data: identityTypes, isLoading } = useQuery({
    queryFn: getRequestTemplateTypes,
    queryKey: ['getRequestTemplateTypes', selfServiceRequest.provider]
  });

  const handleIdentityTypeSelect = useCallback(identityType => {
    setSelectedIdentityType(identityType);
    setSelectedIdentity(null);
    setTypeaheadEndpoint(`/api/v4/templates?template_type=${identityType}`);
    setTypeaheadDefaults({ defaultValue: '', defaultValues: [] });
  }, []);

  const handleTypeaheadSelect = identity => {
    setSelectedIdentity(identity);
  };

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
