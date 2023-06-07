import { useState, useContext } from 'react';
import { Button } from 'shared/elements/Button';
import { AxiosError } from 'axios';

import SelfServiceContext from '../../SelfServiceContext';
import { LineBreak } from 'shared/elements/LineBreak';
import { Block } from 'shared/layout/Block';
import RequestField from './RequestField';
import { ChangeType, ChangeTypeDetails } from '../../types';
import { useQuery } from '@tanstack/react-query';
import { getRequestChangeDetails } from 'core/API/iambicRequest';

interface SelectedOptions {
  [key: string]: string;
}

type RequestChangeDetailsProps = {
  selectedChangeType: ChangeType;
};

const RequestChangeDetails = ({
  selectedChangeType
}: RequestChangeDetailsProps) => {
  const {
    actions: { addChange }
  } = useContext(SelfServiceContext);

  const [changeTypeDetails, setChangeTypeDetails] =
    useState<ChangeTypeDetails | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<SelectedOptions>({});

  const handleChange = (fieldKey: string, value: string) => {
    setSelectedOptions(prev => ({ ...prev, [fieldKey]: value }));
  };

  const { data, isLoading } = useQuery({
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
    <form onSubmit={handleSubmit}>
      {changeTypeDetails?.fields?.map(field => (
        <div key={field.id}>
          <Block
            disableLabelPadding
            key={field.field_key}
            label={field.field_text}
          ></Block>
          <RequestField
            selectedOptions={selectedOptions}
            handleChange={handleChange}
            field={field}
          />
          <LineBreak />
        </div>
      ))}
      <Button
        color="secondary"
        type="submit"
        size="small"
        disabled={!changeTypeDetails}
      >
        Add Change
      </Button>
    </form>
  );
};

export default RequestChangeDetails;
