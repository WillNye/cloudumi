import { useEffect, useState, useContext, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Segment } from 'shared/layout/Segment';
import { Select, SelectOption } from 'shared/form/Select';
import SelfServiceContext from '../../../SelfServiceContext';
import styles from './SelectIdentity.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { TypeaheadBlock } from 'shared/form/TypeaheadBlock';
import {
  getChangeRequestType,
  getRequestTemplateTypes
} from 'core/API/iambicRequest';
import { AxiosError } from 'axios';

const SelectIdentity = () => {
  const [typeaheadDefaults, setTypeaheadDefaults] = useState({
    defaultValue: '',
    defaultValues: []
  });
  const [supportedTemplateTypes, setSupportedTemplateTypes] = useState<
    string[]
  >([]);
  const { selfServiceRequest } = useContext(SelfServiceContext).store;
  const {
    actions: { setSelectedIdentity, setSelectedIdentityType }
  } = useContext(SelfServiceContext);

  const [typeaheadEndpoint, setTypeaheadEndpoint] = useState(
    selfServiceRequest?.identityType
      ? `/api/v4/templates?template_type=${selfServiceRequest?.identityType}`
      : ''
  );

  const { data: identityTypes, isLoading: isLoadingIdentityTypes } = useQuery({
    queryFn: getRequestTemplateTypes,
    queryKey: ['getRequestTemplateTypes', selfServiceRequest.provider]
  });

  const selectedRequestType = useMemo(
    () => selfServiceRequest.requestType,
    [selfServiceRequest]
  );

  const { data: changeTypes, isLoading: isLoadingChangeTypes } = useQuery({
    queryFn: getChangeRequestType,
    queryKey: ['getChangeRequestType', selectedRequestType?.id, false, null],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    }
  });

  useEffect(() => {
    if (changeTypes && changeTypes.data && changeTypes.data.length > 0) {
      const allTemplateTypes = [
        ...new Set(changeTypes.data.flatMap(item => item.template_types))
      ];
      setSupportedTemplateTypes(allTemplateTypes);
    }
  }, [changeTypes]);

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

  const isLoading = isLoadingIdentityTypes || isLoadingChangeTypes;

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
              {identityTypes?.data
                .filter(identityType =>
                  supportedTemplateTypes.includes(identityType.id)
                )
                .map(identityType => (
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
                  selfServiceRequest.identity?.resource_friendly_name ||
                  typeaheadDefaults.defaultValue
                }
                defaultValues={typeaheadDefaults.defaultValues}
                handleOnSelectResult={handleTypeaheadSelect}
                resultsFormatter={result => {
                  return <p>{result.resource_friendly_name}</p>;
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
