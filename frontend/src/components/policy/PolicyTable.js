import React, { useEffect, useState } from 'react'
import { Header } from 'semantic-ui-react'
import DataTable from '../blocks/datatable/DataTableComponent'
import ReactMarkdown from 'react-markdown'
import { useAuth } from '../../auth/AuthProviderDefault'

const PolicyTable = () => {
  const auth = useAuth()
  const { sendRequestCommon } = auth
  const [pageConfig, setPageConfig] = useState(null)

  useEffect(() => {
    ;(async () => {
      const data = await sendRequestCommon(
        null,
        '/api/v2/policies_page_config',
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
      <DataTable config={tableConfig} {...auth} />
    </>
  )
}

export default PolicyTable
