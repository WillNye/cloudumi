import React, { useEffect } from "react";
import { Grid, Table, Segment, Header, Container } from "semantic-ui-react";
import { useAuth } from "./../../auth/AuthProviderDefault";
import { CodeBlock, monokai } from "react-code-blocks";

export const Downloads = () => {
  const { sendRequestCommon } = useAuth();
  const [weepInstallScript, setWeepInstallScript] = React.useState("");
  const [weepDownloadTable, setWeepDownloadTable] = React.useState([]);

  useEffect(() => {
    async function fetchData() {
      const resJson = await sendRequestCommon(
        null,
        "/api/v3/downloads/weep",
        "get"
      );
      if (!resJson) {
        return;
      }
      console.log(resJson);
      setWeepInstallScript(resJson.install_script);
      setWeepDownloadTable(
        resJson.download_links.map((item) => {
          return (
            <Table.Row>
              <Table.Cell>
                <a href={item.download_url}>{item.os_name}</a>
              </Table.Cell>
            </Table.Row>
          );
        })
      );
    }
    fetchData();
  }, [sendRequestCommon]);

  return (
    <Container>
      <Grid>
        <Grid.Column width={16}>
          <Header as="h1">Downloads</Header>
        </Grid.Column>
        <Grid.Column width={16}>
          <Segment>
            Weep is a CLI tool that makes it easy to retrieve and use AWS
            credentials securely. Download weep for your operating system below,
            then run the following command to configure it:
            <br />
            <br />
            {weepInstallScript ? (
              <CodeBlock
                text={weepInstallScript}
                language={"shell"}
                showLineNumbers={false}
                theme={monokai}
              />
            ) : null}
            <br />
            <br />
            {weepDownloadTable ? <Table>{weepDownloadTable}</Table> : null}
          </Segment>
        </Grid.Column>
      </Grid>
    </Container>
  );
};
