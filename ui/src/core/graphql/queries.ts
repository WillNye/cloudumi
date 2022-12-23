import gql from 'graphql-tag';

export const GET_TENANT_USERPOOL_QUERY = gql`
  query GetTenantUserPoolQuery {
    tenantUserPool
      @rest(type: "TenantPool", path: "/api/v1/auth/cognito", method: "GET") {
      data
    }
  }
`;

export const AUTHENTICATE_NOQ_API_QUERY = gql`
  mutation SetupAPIAuth($input: Session!, $encryptor: any) {
    setupAPIAuth: auth(input: $input)
      @rest(
        type: "Post"
        path: "/api/v1/auth/cognito"
        method: "POST"
        bodyBuilder: $encryptor
      ) {
      data
    }
  }
`;

export const GET_ELIGIBLE_ROLES_QUERY = gql`
  query GetEligibleRolesQuery {
    roles
      @rest(
        type: "EligibleRoles"
        path: "/api/v2/eligible_roles"
        method: "GET"
      ) {
      data
      filteredCount
      totalCount
    }
  }
`;
