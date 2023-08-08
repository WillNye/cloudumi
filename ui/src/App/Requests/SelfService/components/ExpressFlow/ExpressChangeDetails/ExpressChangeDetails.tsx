import { useCallback, useMemo, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './ExpressChangeDetails.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../../SelfServiceContext';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getExpressAccessChangeType } from 'core/API/iambicRequest';
import { ProviderDefinition, SelectedOptions } from '../../../types';
import { Button } from 'shared/elements/Button';
import RequestField from '../../common/RequestField';
import { Block } from 'shared/layout/Block';
import RequestExpiration from '../../common/RequestExpiration';
import useGetProviderDefinitions from 'App/Requests/SelfService/hooks/useGetProviderDefinitions';
import IncludedAccounts from '../../common/IncludedAccounts';

const ExpressChangeDetails = () => {
  const [selectedOptions, setSelectedOptions] = useState<SelectedOptions>({});
  const [includedProviders, setIncludedProviders] = useState<
    ProviderDefinition[]
  >([]);

  const {
    actions: { addChange }
  } = useContext(SelfServiceContext);
  const {
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

  const { data: changeTypeDetailsData, isLoading } = useQuery({
    queryFn: getExpressAccessChangeType,
    queryKey: [
      'getExpressAccessChangeType',
      selfServiceRequest?.changeType?.id
    ],
    onSuccess: res => {
      // setSelectedIdentity(res?.data);
    },
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

  const { providerDefinition } = useGetProviderDefinitions({
    provider: selfServiceRequest.provider,
    template_id: changeTypeDetailsData?.data?.iambic_template_id ?? null
  });

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
        included_providers: includedProviders
      });
      setSelectedOptions({});
    },
    [addChange, changeTypeDetails, selectedOptions, includedProviders]
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
                <IncludedAccounts
                  includedProviders={includedProviders}
                  changeTypeDetails={changeTypeDetails}
                  setIncludedProviders={setIncludedProviders}
                  providerDefinition={providerDefinition}
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
