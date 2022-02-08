import React, { useEffect } from "react";
import { Button, Grid, Image, Menu, Segment, Header } from "semantic-ui-react";
import { useAuth } from "./../../auth/AuthProviderDefault";

// function modalReducer(state, action) {
//   switch (action.type) {
//     case "close":
//       return { open: false };
//     case "open":
//       return { open: true, size: action.size };
//     default:
//       throw new Error("Unsupported action...");
//   }
// }

export const Settings = () => {
  const state = { activeItem: "integrations" };
  const { sendRequestCommon } = useAuth();
  const [activeItem, setActiveItem] = React.useState(state.activeItem);
  // const [segment, setSegment] = React.useState();
  const [config, setConfig] = React.useState();

  const handleItemClick = (_, { name }) => setActiveItem(name);

  useEffect(() => {
    async function fetchPageConfig() {
      const resJson = await sendRequestCommon(
        null,
        "/api/v3/integrations/aws",
        "get"
      );
      if (!resJson) {
        return;
      }
      setConfig(resJson?.data);
    }
    fetchPageConfig();
  }, [sendRequestCommon]);

  // const handleAwsConfigureHubAccount = () => {
  //   // TODO - Get a dynamic URL from the backend, duh
  //   // Integrations:
  //   // AWS Accounts:
  //   //    - Run CF Stack, Manually Register, or run script to register through AWS SSO or Manually
  //   //    - Prevent registering account under different tenant
  //   // Sync with AWS organizations
  //   // List existing account integrations
  //   // Only one Central Account allowed
  //   // Multiple Spoke Accounts
  //   // Option to Add Spoke Account
  //   // Option to Remove Spoke Account
  //   // Option to Sync with AWS Organizations
  //   // (v2) - Connection Testing by Assume Role
  //   // AWS Config Integration?
  //   window.open(config?.cloudformation_url_hub_account, "_blank");
  // };

  // const handleAwsConfigureSpokeAccount = () => {
  //   window.open(config?.cloudformation_url_spoke_account, "_blank");
  // };

  return (
    <Grid>
      <Grid.Column width={3}>
        <Menu pointing secondary vertical>
          <Menu.Header>
            <Header as="h2">Integrations</Header>
          </Menu.Header>
          {/* AWS (Event Bridge, User Authentication), Google, Slack, Logging,  */}
          <Menu.Item
            name="aws"
            content="AWS"
            active={activeItem === "aws"}
            onClick={handleItemClick}
          />
          {/* SSO Integrations, who is an admin in Noq? */}
          <Menu.Item
            name="authentication"
            active={activeItem === "authentication"}
            onClick={handleItemClick}
          />
          {/* Pricing tiers, free tier vs others */}
          <Menu.Item
            name="billing"
            active={activeItem === "billing"}
            onClick={handleItemClick}
          />
          {/* Determine what to show users for support contacts/messaging */}
          {/* Enterprise tier mentions support for data plane in customer account */}
          <Menu.Item
            name="customization"
            active={activeItem === "customization"}
            onClick={handleItemClick}
          />
        </Menu>
      </Grid.Column>
      <Grid.Column stretched width={12}>
        {activeItem === "aws" ? (
          <Grid columns={2}>
            <Grid.Row>
              <Grid.Column>
                <Grid columns={1}>
                  <Grid.Row>
                    <Segment>
                      <Image
                        src="/images/logos/aws.svg"
                        size="small"
                        centered
                      />
                      <br />
                      The AWS integration allows NOQ to manage AWS access,
                      permissions, and resources for your accounts.
                      <Header as="h2">Central Account</Header>
                      Your central account is an AWS account of your choosing
                      that will be the entrypoint for Noq into your environment.
                      We will help you create a role on this account that Noq
                      will assume. Noq will assume this role before assuming
                      other roles in your environment.
                      <br />
                      <br />
                      <Header as="h3">Automatic Setup</Header>
                      {config?.central_account_role?.cloudformation_url ? (
                        <div>
                          <a
                            href={
                              config.central_account_role.cloudformation_url
                            }
                          >
                            Click here
                          </a>{" "}
                          to setup NOQ's role in your account automatically with
                          a Cloudformation stack. After the role has been
                          created, the stack will call back to an SNS topic
                          owned by NOQ to register your account.
                        </div>
                      ) : null}
                      <Header as="h3">Manual Setup</Header>
                      {config?.central_account_role
                        ?.central_role_trust_policy ? (
                        <div>
                          You can create a role manually by following the
                          instructions below: 1) Create a role in your account
                          with the following trust policy:
                          <br />
                          <pre>
                            {
                              config.central_account_role
                                .central_role_trust_policy
                            }
                          </pre>
                        </div>
                      ) : null}
                      {config?.central_account_role?.external_id ? (
                        <div>
                          External ID: {config.central_account_role.external_id}
                        </div>
                      ) : null}
                      {config?.central_account_role?.node_role ? (
                        <div>
                          Node Role: {config.central_account_role.node_role}
                        </div>
                      ) : null}
                      <Header as="h2">Spoke Accounts</Header>
                      Your spoke accounts are all of the AWS accounts that you
                      want to use Noq in. We will help you create spoke roles on
                      these accounts. Noq will access these roles by first
                      assuming your central account role and then assuming the
                      spoke roles.
                      <Header as="h3">Automatic Setup</Header>
                      {config?.spoke_account_role?.cloudformation_url ? (
                        <div>
                          <a
                            href={config.spoke_account_role.cloudformation_url}
                          >
                            Click here
                          </a>{" "}
                          to setup a Noq spoke role in your account
                          automatically with a Cloudformation stack. After the
                          role has been created, the stack will call back to an
                          SNS topic owned by NOQ to register your account.
                        </div>
                      ) : null}
                    </Segment>
                  </Grid.Row>
                </Grid>
              </Grid.Column>
              {/* <Grid.Column>
                <Grid columns={2} divided padded>
                  <Grid.Row>
                    <Segment>
                      <Image
                        src="/images/logos/slack.svg"
                        size="tiny"
                        circular
                        centered
                      />
                      <br />
                      <Button icon="settings" content="Configure" />
                    </Segment>
                  </Grid.Row>
                </Grid>
              </Grid.Column>
              <Grid.Column>
                <Grid columns={2} divided padded>
                  <Grid.Row>
                    <Segment>
                      <Image
                        src="/images/logos/google.svg"
                        size="tiny"
                        circular
                        centered
                      />
                      <br />
                      <Button icon="settings" content="Configure" />
                    </Segment>
                  </Grid.Row>
                </Grid>
              </Grid.Column> */}
            </Grid.Row>
          </Grid>
        ) : null}

        {activeItem === "authentication" ? (
          <Grid columns={5}>
            <Grid.Row>
              <Grid.Column>
                <Grid columns={2} divided padded>
                  <Grid.Row>
                    TODO: Logos for specific providers, ie: Okta, Cognito, AWS
                    SSO, Google, etc.
                    <Segment>
                      <Image
                        src="/images/logos/openid.svg"
                        size="tiny"
                        circular
                        centered
                      />
                      <br />
                      <Button icon="settings" content="Configure" />
                      OpenID settings required: - Client ID - Client Secret -
                      Client Scopes (e.g. openid, profile, email) - Metadata URL
                      - Advanced options: - jwt_email_key, jwt_groups_key,
                      access_token_audience
                    </Segment>
                  </Grid.Row>
                </Grid>
              </Grid.Column>
              <Grid.Column>
                <Grid columns={2} divided padded>
                  <Grid.Row>
                    <Segment>
                      <Image
                        src="/images/logos/saml.png"
                        size="tiny"
                        circular
                        centered
                      />
                      <br />
                      <Button icon="settings" content="Configure" />
                    </Segment>
                  </Grid.Row>
                </Grid>
              </Grid.Column>
            </Grid.Row>
          </Grid>
        ) : null}
      </Grid.Column>
    </Grid>
  );
};
