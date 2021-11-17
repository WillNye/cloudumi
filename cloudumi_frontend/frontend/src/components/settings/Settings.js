import React, { useEffect, Component } from "react";
import { Button, Grid, Menu, Segment, Image } from "semantic-ui-react";
import { useAuth } from "./../../auth/AuthProviderDefault";

function modalReducer(state, action) {
  switch (action.type) {
    case "close":
      return { open: false };
    case "open":
      return { open: true, size: action.size };
    default:
      throw new Error("Unsupported action...");
  }
}

export const Settings = () => {
  const state = { activeItem: "integrations" };
  const { sendRequestCommon } = useAuth();
  const [activeItem, setActiveItem] = React.useState(state.activeItem);
  const [segment, setSegment] = React.useState();
  const [config, setConfig] = React.useState();

  const handleItemClick = (e, { name }) => setActiveItem(name);

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
      setConfig(resJson);
    }
    fetchPageConfig();
  }, [sendRequestCommon]);

  const handleAwsConfigureHubAccount = () => {
    // TODO - Get a dynamic URL from the backend, duh
    // Integrations:
    // AWS Accounts:
    //    - Run CF Stack, Manually Register, or run script to register through AWS SSO or Manually
    //    - Prevent registering account under different tenant
    // Sync with AWS organizations
    // List existing account integrations
    // Only one Central Account allowed
    // Multiple Spoke Accounts
    // Option to Add Spoke Account
    // Option to Remove Spoke Account
    // Option to Sync with AWS Organizations
    // (v2) - Connection Testing by Assume Role
    // AWS Config Integration?
    window.open(config?.cloudformation_url_hub_account, "_blank");
  };

  const handleAwsConfigureSpokeAccount = () => {
    window.open(config?.cloudformation_url_spoke_account, "_blank");
  };

  return (
    <Grid>
      <Grid.Column width={4}>
        <Menu pointing secondary vertical>
          {/* AWS (Event Bridge, User Authentication), Google, Slack, Logging,  */}
          <Menu.Item
            name="integrations"
            active={activeItem === "integrations"}
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
        {activeItem === "integrations" ? (
          <Grid columns={5}>
            <Grid.Row>
              <Grid.Column>
                <Grid columns={2} divided padded>
                  <Grid.Row>
                    <Segment>
                      <Image
                        src="/images/logos/aws.svg"
                        size="tiny"
                        circular
                        centered
                      />
                      <br />
                      <Button
                        icon="settings"
                        content="Configure Hub Account"
                        onClick={handleAwsConfigureHubAccount}
                      />
                      <Button
                        icon="settings"
                        content="Configure Spoke Account"
                        onClick={handleAwsConfigureSpokeAccount}
                      />
                    </Segment>
                  </Grid.Row>
                </Grid>
              </Grid.Column>
              <Grid.Column>
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
              </Grid.Column>
            </Grid.Row>
          </Grid>
        ) : null}

        {activeItem === "authentication" ? (
          <Grid columns={5}>
            <Grid.Row>
              <Grid.Column>
                <Grid columns={2} divided padded>
                  <Grid.Row>
                    <Segment>
                      <Image
                        src="/images/logos/openid.svg"
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
