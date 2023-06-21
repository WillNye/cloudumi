import { useState, useContext, useEffect, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { Segment } from 'shared/layout/Segment';
import { Select, SelectOption } from 'shared/form/Select';
import SelfServiceContext from '../../SelfServiceContext';
import axios from 'core/Axios/Axios';
import styles from './SelectIdentity.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { TypeaheadBlock } from 'shared/form/TypeaheadBlock';

const SelectIdentity = () => {
  const [typeaheadDefaults, setTypeaheadDefaults] = useState({
    defaultValue: '',
    defaultValues: []
  });
  const [identityTypes, setIdentityTypes] = useState([]);
  const [typeaheadEndpoint, setTypeaheadEndpoint] = useState('');
  const { selfServiceRequest } = useContext(SelfServiceContext).store;
  const {
    actions: { setSelectedIdentity, setSelectedIdentityType }
  } = useContext(SelfServiceContext);

  useEffect(() => {
    axios
      .get(`/api/v4/template-types?provider=${selfServiceRequest.provider}`)
      .then(response => setIdentityTypes(response?.data?.data))
      .catch(error => console.error(error));
  }, [selfServiceRequest.provider]);

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
    <Segment>
      <div className={styles.container}>
        <h3>Select Identity Type</h3>
        <LineBreak />
        <p className={styles.subText}>Please select an identity type</p>
        <LineBreak size="large" />
        <div className={styles.content}>
          {identityTypes && (
            <Select
              value={selfServiceRequest.identityType || ''}
              onChange={handleIdentityTypeSelect}
              placeholder="Select identity type"
            >
              {identityTypes.map(identityType => (
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
