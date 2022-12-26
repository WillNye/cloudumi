import gql from 'graphql-tag';

export const GET_TENANT_USERPOOL_QUERY = gql`
  query GetTenantUserPoolQuery {
    tenantUserPool
      @rest(type: "TenantPool", path: "/api/v1/auth/settings", method: "GET") {
      data
    }
  }
`;

// TODO Kayizzi: If the user is authenticated, this query will return with a `user` username attribute
// in the response. We should setUser with this user instead of the one from Cognito
export const GET_SSO_AUTH_REDIRECT_QUERY = gql`
  query WebResponse {
    ssoAuthRedirect
      @rest(
        type: "SSOAuth"
        path: "/api/v1/auth?sso_signin=true"
        method: "GET"
      ) {
      redirect_url
      user
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

export const USER_SEND_RESET_PASSWORD_LINK = gql`
  mutation SetupAPIAuth($input: Session!, $encryptor: any) {
    setupAPIAuth: auth(input: $input)
      @rest(
        type: "Post"
        path: "/api/v4/users/forgot_password"
        method: "POST"
        bodyBuilder: $encryptor
      ) {
      data
    }
  }
`;
