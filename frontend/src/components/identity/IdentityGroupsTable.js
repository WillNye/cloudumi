import React, { useEffect, useState } from 'react'
import { Header, Button } from 'semantic-ui-react'
import ConsoleMeDataTable from '../blocks/datatable/DataTableComponent'
import ReactMarkdown from 'react-markdown'
import { useAuth } from '../../auth/AuthProviderDefault'

const IdentityGroupsTable = () => {
  const auth = useAuth()
  const { sendRequestCommon } = auth
  const [pageConfig, setPageConfig] = useState(null)

  useEffect(() => {
    ;(async () => {
      const data = await sendRequestCommon(
        null,
        '/api/v3/identities/groups_page_config',
        'get'
      )
      if (!data) {
        return
      }
      setPageConfig(data)
    })()
  }, [sendRequestCommon])

  if (!pageConfig) {
    return null
  }

  const { pageName, pageDescription, tableConfig } = pageConfig

  return (
    <>
      <Header as='h1'>
        {pageName}
        <Header.Subheader>
          <ReactMarkdown
            escapeHtml={false}
            linkTarget='_blank'
            children={pageDescription}
          />
        </Header.Subheader>
      </Header>
      <Button basic color='blue' icon='refresh'></Button>
      <Button basic color='blue'>
        Add Group
      </Button>
      <ConsoleMeDataTable config={tableConfig} {...auth} />
    </>
  )
}

export default IdentityGroupsTable
