import { RestLink } from 'apollo-link-rest';

// Note: This is just a stop gap until the GraphQL API is ready
export const restLink = new RestLink({
  uri: import.meta.env.VITE_API_URL,
  credentials: "same-origin"
});
