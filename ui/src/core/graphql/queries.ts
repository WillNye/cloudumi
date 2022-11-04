import gql from 'graphql-tag';

export const GET_TENANT_USERPOOL_QUERY = gql`
  query GetTenantUserPoolQuery {
    listUsers @rest(type: "User", path: "/api/v3/tenant/userpool") {
      start
    }
  }
`;
