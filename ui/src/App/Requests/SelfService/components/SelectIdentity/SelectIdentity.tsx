import { useState, useContext, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { Segment } from 'shared/layout/Segment';
import { Select, SelectOption } from 'shared/form/Select';
import SelfServiceContext from '../../SelfServiceContext';
import axios from 'core/Axios/Axios';
import styles from './SelectIdentqityType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { SELF_SERVICE_STEPS } from '../../constants';
import { TypeaheadBlock } from 'shared/form/TypeaheadBlock';
import { set } from 'date-fns';

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

  const handleIdentityTypeSelect = identityType => {
    setSelectedIdentityType(identityType);
    setSelectedIdentity(null);
    setTypeaheadEndpoint(`/api/v4/templates?template_type=${identityType}`);
    setTypeaheadDefaults({ defaultValue: '', defaultValues: [] });
  };

  const handleTypeaheadSelect = identity => {
    setSelectedIdentity(identity);
  };

  return (
    <Segment>
      <h3>Select Identity Type</h3>
      <LineBreak />
      <p>Please select an identity type</p>
      <LineBreak size="large" />
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
          {/* TODO: Typeahead block should support selecting a single element */}
          <TypeaheadBlock
            defaultValue={typeaheadDefaults.defaultValue}
            defaultValues={typeaheadDefaults.defaultValues}
            // handleInputUpdate={handleTypeaheadSelect}
            resultsFormatter={result => {
              console.log('result', result);
              return <p>{result.resource_id}</p>;
            }}
            endpoint={typeaheadEndpoint}
            queryParam={'resource_id'}
            titleKey={'resource_id'}
          />
        </>
      )}
    </Segment>
  );
};

export default SelectIdentity;
