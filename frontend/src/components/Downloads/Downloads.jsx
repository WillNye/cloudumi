import React, { useEffect } from 'react'
import { Grid, Table, Segment, Header } from 'semantic-ui-react'
import { useAuth } from '../../auth/AuthProviderDefault'
import { CopyBlock, dracula } from 'react-code-blocks'

const Downloads = () => {
  const { sendRequestCommon } = useAuth()
  const [noqInstallScript, setNoqInstallScript] = React.useState('')
  const [noqDownloadTable, setNoqDownloadTable] = React.useState([])

  useEffect(() => {
    async function fetchData() {
      const resJson = await sendRequestCommon(
        null,
        '/api/v3/downloads/noq',
        'get'
      )
      if (!resJson) {
        return
      }

      setNoqInstallScript(resJson.install_script)
      setNoqDownloadTable(
        resJson.download_links.map((item) => {
          return (
            <Table.Row>
              <Table.Cell>
                <a href={item.download_url}>{item.os_name}</a>
              </Table.Cell>
            </Table.Row>
          )
        })
      )
    }
    fetchData()
  }, [sendRequestCommon])

  return (
    <Grid>
      <Grid.Column width={16}>
        <Header as='h1'>Downloads</Header>
      </Grid.Column>
      <Grid.Column width={8}>
        <Segment>
          The NOQ CLI tool makes it easy to retrieve and use AWS credentials
          securely, when paired with the NOQ Cloud platform. Download `noq` CLI
          for your operating system below, then run the following command to
          configure it:
          <br />
          <br />
          {noqInstallScript ? (
            <CopyBlock
              text={noqInstallScript}
              language={'shell'}
              showLineNumbers={false}
              theme={dracula}
            />
          ) : null}
          <br />
          <br />
          {noqDownloadTable ? <Table>{noqDownloadTable}</Table> : null}
        </Segment>
      </Grid.Column>
    </Grid>
  )
}

export default Downloads
