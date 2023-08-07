import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getProviderDefinitions } from 'core/API/iambicRequest';

const useGetProviderDefinitions = ({ provider, template_id }) => {
  // console
  const { data: providerDefinitions, isLoading: loadingDefinitions } = useQuery(
    {
      queryFn: getProviderDefinitions,
      queryKey: [
        'getProviderDefinitions',
        {
          provider,
          template_id
        }
      ],
      onError: (error: AxiosError) => {
        // const errorRes = error?.response;
        // const errorMsg = extractErrorMessage(errorRes?.data);
        // setErrorMessage(errorMsg || 'An error occurred fetching resource');
      }
    }
  );
  return { providerDefinitions };
};

export default useGetProviderDefinitions;
