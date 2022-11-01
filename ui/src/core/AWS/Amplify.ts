import { Amplify } from 'aws-amplify';

/**
 * References
 *  - https://docs.amplify.aws/lib/auth/emailpassword/q/platform/js
 *  - https://stackoverflow.com/questions/66701358/how-to-use-amazon-cognito-without-amplify
 *  - https://github.com/dbroadhurst/aws-cognito-react
 * 
 * Dev reference:
 *   * cloudumi_tenant_dev-267095_noq_localhost
 *   * arn:aws:cognito-idp:us-east-1:759357822767:userpool/us-east-1_CNoZribID
 */
Amplify.configure({
  // Reference:
  Auth: {
    // // REQUIRED only for Federated Authentication - Amazon Cognito Identity Pool ID
    // identityPoolId: 'us-east-1_CNoZribID',

    // REQUIRED - Amazon Cognito Region
    region: 'us-east-1',

    // OPTIONAL - Amazon Cognito Federated Identity Pool Region
    // Required only if it's different from Amazon Cognito Region
    // identityPoolRegion: 'XX-XXXX-X',

    // OPTIONAL - Amazon Cognito User Pool ID
    userPoolId: 'us-east-1_CNoZribID',

    // OPTIONAL - Amazon Cognito Web Client ID (26-char alphanumeric string)
    userPoolWebClientId: '6f44pcgu8dk978njp3frkt9p1k'
  }
});
