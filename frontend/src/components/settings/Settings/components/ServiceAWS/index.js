import React, { useEffect } from 'react';
import { Grid, Image, Segment, Header } from 'semantic-ui-react';
import { useAuth } from '../../../../../auth/AuthProviderDefault';

const ServiceAWS = () => {

  const state = { activeItem: "integrations" };
  const { sendRequestCommon } = useAuth();
  const [activeItem, setActiveItem] = React.useState(state.activeItem);

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

  return (
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
      </Grid.Row>
    </Grid>    
  );
};

export default ServiceAWS;