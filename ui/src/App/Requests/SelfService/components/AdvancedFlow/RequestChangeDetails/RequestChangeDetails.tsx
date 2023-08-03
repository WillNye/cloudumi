import { useEffect, useState, useContext, useMemo } from 'react';
import { Button } from 'shared/elements/Button';
import { AxiosError } from 'axios';

import SelfServiceContext from '../../../SelfServiceContext';
import { LineBreak } from 'shared/elements/LineBreak';
import { Block } from 'shared/layout/Block';
import RequestField from '../../common/RequestField';
import { ChangeType, ChangeTypeDetails, SelectedOptions } from '../../../types';
import { useQuery } from '@tanstack/react-query';
import { getRequestChangeDetails } from 'core/API/iambicRequest';
import { Segment } from 'shared/layout/Segment';
import { Select, SelectOption } from 'shared/form/Select';
import { ProviderDefinition } from '../../../types';

type RequestChangeDetailsProps = {
  selectedChangeType: ChangeType;
  providerDefinition: ProviderDefinition[];
};

const RequestChangeDetails = ({
  selectedChangeType,
  providerDefinition
}: RequestChangeDetailsProps) => {
  const {
    actions: { addChange },
    store: { selfServiceRequest }
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

  const providerDefinitionFields = useMemo(() => {
    if (changeTypeDetails?.provider_definition_field == 'Allow Multiple') {
      return 'multiple';
    } else if (changeTypeDetails?.provider_definition_field == 'Allow One') {
      return 'single';
    }
    return null;
  }, [changeTypeDetails]);

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
      setChangeTypeDetails(data as unknown as ChangeTypeDetails);
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
      })),
      included_providers: includedProviders
    });
    setSelectedOptions({});
  };

  const accountNamesValue = useMemo(() => {
    // on multiple selects, the value is an array of strings
    // on single selects, the value is a string
    if (providerDefinitionFields === 'multiple') {
      return includedProviders.map(
        provider => provider.definition.account_name
      );
    } else if (providerDefinitionFields === 'single') {
      return includedProviders.length > 0
        ? includedProviders[0]?.definition.account_name
        : null;
    }
    return null;
  }, [includedProviders, providerDefinitionFields]);

  const handleOnChangeAccountName = (value: any[] | any) => {
    // refer to accountNamesValue for explanation of value
    let selectedProviders = [];
    if (Array.isArray(value)) {
      selectedProviders = providerDefinition.filter(provider =>
        value.includes(provider.definition.account_name)
      );
    } else {
      selectedProviders = providerDefinition.filter(
        provider => value == provider.definition.account_name
      );
    }

    setIncludedProviders(selectedProviders);
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
        {selfServiceRequest?.provider === 'aws' &&
          providerDefinitionFields != null && (
            <>
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
                multiple={providerDefinitionFields === 'multiple'}
                value={accountNamesValue}
                onChange={handleOnChangeAccountName}
                closeOnSelect={providerDefinitionFields === 'single'}
              >
                {providerDefinition?.map(def => (
                  <SelectOption
                    key={def.id}
                    value={def.definition.account_name}
                  >
                    {def.definition.account_name}
                  </SelectOption>
                ))}
              </Select>
            </>
          )}
        <LineBreak />
        <Button type="submit" size="small" disabled={!changeTypeDetails}>
          Add Change
        </Button>
      </form>
    </Segment>
  );
};

export default RequestChangeDetails;
