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
                + - os: macos_installer
                {/* +      url: https://public-weep-binaries.s3.us-west-2.amazonaws.com/macos_installer/weep-installer-macos-v0.3.24.pkg
+    - os: darwin_arm64
+      url: https://public-weep-binaries.s3.us-west-2.amazonaws.com/darwin_arm64/weep
+    - os: darwin_x86_64
+      url: https://public-weep-binaries.s3.us-west-2.amazonaws.com/darwin_x86_64/weep
+    - os: linux_arm64
+      url: https://public-weep-binaries.s3.us-west-2.amazonaws.com/linux_arm64/weep
+    - os: linux_i386
+      url: https://public-weep-binaries.s3.us-west-2.amazonaws.com/linux_i386/weep
+    - os: linux_x86_64
+      url: https://public-weep-binaries.s3.us-west-2.amazonaws.com/linux_x86_64/weep
+    - os: windows_arm64
+      url: https://public-weep-binaries.s3.us-west-2.amazonaws.com/windows_arm64/weep.exe
+    - os: windows_i386
+      url: https://public-weep-binaries.s3.us-west-2.amazonaws.com/windows_i386/weep.exe
+    - os: windows_x86_64
+      url: https://public-weep-binaries.s3.us-west-2.amazonaws.com/windows_x86_64/weep.exe */}
                <Table.Cell>
                  <a
                    href="https://public-weep-binaries.s3.us-west-2.amazonaws.com/macos_installer/weep-installer-macos-v0.3.24.pkg"
                    Mac
                    Installer
                  />
                </Table.Cell>
              </Table.Row>
            </Table>
          </Segment>
        </Grid.Column>
      </Grid>
    </Container>
  );
};
