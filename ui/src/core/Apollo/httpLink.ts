import { createHttpLink } from '@apollo/client';

export const httpLink = createHttpLink({
  uri: import.meta.env.VITE_API_URL
});
