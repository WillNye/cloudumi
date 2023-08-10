import { useContext, useMemo } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { Block } from 'shared/layout/Block';
import { Select, SelectOption } from 'shared/form/Select';

const IncludedAccounts = ({
  changeTypeDetails,
  includedProviders,
  providerDefinition,
  setIncludedProviders
}) => {
  const {
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

  const providerDefinitionFields = useMemo(() => {
    if (changeTypeDetails?.provider_definition_field == 'Allow Multiple') {
      return 'multiple';
    } else if (changeTypeDetails?.provider_definition_field == 'Allow One') {
      return 'single';
    }
    return null;
  }, [changeTypeDetails]);

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
      selectedProviders = providerDefinition?.filter(provider =>
        value.includes(provider.definition.account_name)
      );
    } else {
      selectedProviders = providerDefinition?.filter(
        provider => value == provider.definition.account_name
      );
    }
    setIncludedProviders(selectedProviders);
  };

  return (
    <>
      {selfServiceRequest?.provider === 'aws' &&
        providerDefinitionFields != null && (
          <>
            <Block
              disableLabelPadding
              key="includedAccounts"
              label="Included Accounts"
              required
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
                <SelectOption key={def.id} value={def.definition.account_name}>
                  {def.definition.account_name}
                </SelectOption>
              ))}
            </Select>
          </>
        )}
    </>
  );
};

export default IncludedAccounts;
