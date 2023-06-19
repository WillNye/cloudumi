import { useEffect, useState, useContext } from 'react';
import { Button } from 'shared/elements/Button';
import { AxiosError } from 'axios';

import SelfServiceContext from '../../SelfServiceContext';
import { LineBreak } from 'shared/elements/LineBreak';
import { Block } from 'shared/layout/Block';
import RequestField from './RequestField';
import { ChangeType, ChangeTypeDetails } from '../../types';
import { useQuery } from '@tanstack/react-query';
import { getRequestChangeDetails } from 'core/API/iambicRequest';
import { Segment } from 'shared/layout/Segment';
import { Select, SelectOption } from 'shared/form/Select';

interface SelectedOptions {
  [key: string]: string;
}

type ProviderDefinition = {
  id: string;
  name: string;
  provider: string;
  definition: {
    account_id: string;
    account_name: string;
    variables: Array<{ key: string; value: string }>;
    org_id: string;
    preferred_identifier: string;
    all_identifiers: string[];
  };
};

type RequestChangeDetailsProps = {
  selectedChangeType: ChangeType;
  providerDefinition: ProviderDefinition[];
};

const RequestChangeDetails = ({
  selectedChangeType,
  providerDefinition
}: RequestChangeDetailsProps) => {
  const {
    actions: { addChange }
  } = useContext(SelfServiceContext);

  const [changeTypeDetails, setChangeTypeDetails] =
    useState<ChangeTypeDetails | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<SelectedOptions>({});
  const [includedProviders, setIncludedProviders] = useState<
    ProviderDefinition[]
  >([]);

  const handleChange = (fieldKey: string, value: string) => {
    setSelectedOptions(prev => ({ ...prev, [fieldKey]: value }));
  };

  useEffect(() => {
    if (providerDefinition?.length === 1) {
      setIncludedProviders([providerDefinition[0]]);
    }
  }, [providerDefinition]);

  const { isLoading } = useQuery({
    queryFn: getRequestChangeDetails,
    queryKey: [
      'getChangeRequestType',
      selectedChangeType.request_type_id,
      selectedChangeType.id
    ],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    },
    onSuccess: ({ data }) => {
      setChangeTypeDetails(data);
    }
  });

  const handleSubmit = e => {
    e.preventDefault();
    addChange({
      id: changeTypeDetails.id,
      name: changeTypeDetails.name,
      description: changeTypeDetails.description,
      request_type_id: changeTypeDetails.request_type_id,
      fields: changeTypeDetails.fields.map(field => ({
        ...field,
        value: selectedOptions[field.field_key]
      }))
    });
    setSelectedOptions({});
  };

  return (
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
        <Block
          disableLabelPadding
          key={'Included Accounts'}
          label={'Included Accounts'}
          required={true}
        ></Block>
        <Select
          id="accountNames"
          name="accountNames"
          placeholder="Select account(s)"
          multiple
          value={includedProviders.map(
            provider => provider.definition.account_name
          )}
          onChange={value => {
            const selectedProviders = providerDefinition.filter(provider =>
              value.includes(provider.definition.account_name)
            );
            setIncludedProviders(selectedProviders);
          }}
          closeOnSelect={false}
        >
          {providerDefinition?.map(def => (
            <SelectOption key={def.id} value={def.definition.account_name}>
              {def.definition.account_name}
            </SelectOption>
          ))}
        </Select>
        <LineBreak />
        <Button type="submit" size="small" disabled={!changeTypeDetails}>
          Add Change
        </Button>
      </form>
    </Segment>
  );
};

export default RequestChangeDetails;
