import { QueryClient } from '@tanstack/react-query';

export const invalidateSsoQueries = (queryClient: QueryClient) => {
  queryClient.invalidateQueries({ queryKey: [`samlSettings`] });
  queryClient.invalidateQueries({ queryKey: [`oidcSettings`] });
  queryClient.invalidateQueries({ queryKey: [`authSettings`] });
};
