import React, { useEffect } from "react";
import {
  Button,
  Grid,
  Table,
  Image,
  Menu,
  Segment,
  Header,
  Container,
} from "semantic-ui-react";
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

export const Downloads = () => {
  return (
    <Container>
      <Grid>
        <Grid.Column width={16}>
          <Header as="h1">Downloads</Header>
        </Grid.Column>
        <Grid.Column width={16}>
          <Segment>
            Weep is a CLI tool that makes it easy to retrieve and use AWS
            credentials securely. Download Weep for your operating system, and
            follow the guidance below to configure it.
            <Table>
              <Table.Row>
                <Table.Cell>
                  <a href="f" />
                </Table.Cell>
              </Table.Row>
            </Table>
          </Segment>
        </Grid.Column>
      </Grid>
    </Container>
  );
};
