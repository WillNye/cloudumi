import { useCallback, useEffect, useMemo, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './ExpressChangeDetails.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../../SelfServiceContext';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getExpressAccessChangeType } from 'core/API/iambicRequest';
import { ChangeType, Identity, SelectedOptions } from '../../../types';
import { SELF_SERVICE_STEPS } from '../../../constants';
import { Card } from 'shared/layout/Card';
import { Search } from 'shared/form/Search';
import { Button } from 'shared/elements/Button';
import { Link } from 'react-router-dom';
import RequestField from '../../common/RequestField';
import { Block } from 'shared/layout/Block';
import RequestExpiration from '../../common/RequestExpiration';

const ExpressChangeDetails = () => {
  const [selectedOptions, setSelectedOptions] = useState<SelectedOptions>({});

  const {
    actions: { addChange, setSelectedIdentity, setSelectedIdentityType }
  } = useContext(SelfServiceContext);
  const {
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

  const [selectedCard, setSelectedCard] = useState(null);

  const handleCardClick = identity => {
    if (selectedCard === identity.resource_id) {
      setSelectedIdentity(null);
      setSelectedCard(null);
      setSelectedIdentityType(null);
    } else {
      setSelectedIdentityType(identity.template_type);
      setSelectedIdentity(identity);
      setSelectedCard(identity.resource_id);
    }
  };

  const { data: changeTypeDetailsData, isLoading } = useQuery({
    queryFn: getExpressAccessChangeType,
    queryKey: [
      'getExpressAccessChangeType',
      selfServiceRequest?.changeType?.id
    ],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    }
  });

  const changeTypeDetails = useMemo(
    () => changeTypeDetailsData?.data?.change_type,
    [changeTypeDetailsData]
  );

  const handleChange = (fieldKey: string, value: string) => {
    setSelectedOptions(prev => ({ ...prev, [fieldKey]: value }));
  };

  const handleSubmit = useCallback(
    e => {
      e.preventDefault();
      if (!changeTypeDetails) {
        return;
      }
      addChange({
        id: changeTypeDetails.id,
        name: changeTypeDetails.name,
        description: changeTypeDetails.description,
        request_type_id: changeTypeDetails.request_type_id,
        fields: changeTypeDetails.fields.map(field => ({
          ...field,
          value: selectedOptions[field.field_key]
        })),
        included_providers: []
      });
      setSelectedOptions({});
    },
    [addChange, changeTypeDetails, selectedOptions]
  );

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Which Cloud Identity would you like to add this to?</h3>
        <LineBreak />
        <p className={styles.subText}>
          Please select one of the suggested identities below
        </p>
        <LineBreak />
        <Segment isLoading={isLoading} disablePadding>
          <form onSubmit={handleSubmit}>
            {changeTypeDetails?.fields?.map(field => (
              <div key={field.id}>
                <Block
                  disableLabelPadding
                  key={field.field_key}
                  label={field.field_text}
                  required={!field.allow_none}
                ></Block>
                <RequestField
                  selectedOptions={selectedOptions}
                  handleChange={handleChange}
                  field={field}
                />
                <LineBreak />
              </div>
            ))}
            <Button type="submit" size="small" disabled={!changeTypeDetails}>
              Add Change
            </Button>
            <RequestExpiration />
          </form>
        </Segment>
      </div>
    </Segment>
  );
};

export default ExpressChangeDetails;
