import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getProviderDefinitions } from 'core/API/iambicRequest';

const useGetProviderDefinitions = ({
  provider,
  template_id,
  template_type
}) => {
  const { data: providerDefinition, isLoading: loadingDefinitions } = useQuery({
    queryFn: getProviderDefinitions,
    queryKey: [
      'getProviderDefinitions',
      {
        provider,
        template_id,
        template_type
      }
    ],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    }
  });
  return { providerDefinition };
};

export default useGetProviderDefinitions;
