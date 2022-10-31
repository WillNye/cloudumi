import { CognitoUser } from '@aws-amplify/auth';

export interface User extends CognitoUser {
  authenticationFlowType: string;
  preferredMFA: string;
  attributes: {
    email: string;
    email_verified: boolean;
    sub: string;
  };
}
