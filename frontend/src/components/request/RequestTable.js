import React, { useEffect, useState } from 'react'
import { Header } from 'semantic-ui-react'
import ConsoleMeDataTable from '../blocks/datatable/DataTableComponent'
import { useAuth } from '../../auth/AuthProviderDefault'
import ReactMarkdown from 'react-markdown'

const RequestTable = () => {
  const [pageConfig, setPageConfig] = useState(null)
  const auth = useAuth()
  const { sendRequestCommon } = auth

  useEffect(() => {
    ;(async () => {
      const data = await sendRequestCommon(
        null,
        '/api/v2/requests_page_config',
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
      <ConsoleMeDataTable config={tableConfig} {...auth} mock={[
  {
    "last_updated": 1644793727,
    "version": "2",
    "extended_request": {
      "request_status": "approved",
      "cross_account": false,
      "comments": [
        {
          "user_email": "curtis@noq.dev",
          "edited": null,
          "id": "36253f65-d091-4942-86a7-1bdb879e01c3",
          "text": "Self-approved by admin: curtis@noq.dev",
          "last_modified": "2022-02-13T23:08:42+00:00",
          "user": {
            "extended_info": {
              "name": {
                "fullName": "---DYNAMO-EMPTY-STRING---",
                "givenName": "---DYNAMO-EMPTY-STRING---",
                "familyName": "---DYNAMO-EMPTY-STRING---"
              },
              "userName": "curtis@noq.dev",
              "primaryEmail": "curtis@noq.dev",
              "domain": "---DYNAMO-EMPTY-STRING---"
            },
            "photo_url": "https://www.gravatar.com/avatar/35f0aa0d90d6fdfb178a847bd5ae5e6c?d=mp",
            "details_url": null,
            "email": "curtis@noq.dev"
          },
          "timestamp": "2022-02-13T23:08:42+00:00"
        }
      ],
      "changes": {
        "changes": [
          {
            "original_value": null,
            "original_key": null,
            "resources": [],
            "autogenerated": false,
            "change_type": "resource_tag",
            "version": "3.0",
            "principal": {
              "principal_type": "AwsResource",
              "principal_arn": "arn:aws:iam::259868150464:role/faa"
            },
            "tag_action": "delete",
            "updated_by": "curtis@noq.dev",
            "id": "b48dabb4-6471-4388-ae09-9f6814430fd00",
            "value": null,
            "key": "noq-authorized",
            "status": "applied"
          }
        ]
      },
      "approvers": [],
      "requester_email": "curtis@noq.dev",
      "reviewer": "curtis@noq.dev",
      "request_url": null,
      "principal": {
        "principal_type": "AwsResource",
        "principal_arn": "arn:aws:iam::259868150464:role/faa"
      },
      "arn_url": "---DYNAMO-EMPTY-STRING---",
      "admin_auto_approve": true,
      "id": "b48dabb4-6471-4388-ae09-9f6814430fd0",
      "justification": "test",
      "timestamp": "2022-02-13T23:08:41+00:00",
      "requester_info": {
        "extended_info": {
          "name": {
            "fullName": "---DYNAMO-EMPTY-STRING---",
            "givenName": "---DYNAMO-EMPTY-STRING---",
            "familyName": "---DYNAMO-EMPTY-STRING---"
          },
          "userName": "curtis@noq.dev",
          "primaryEmail": "curtis@noq.dev",
          "domain": "---DYNAMO-EMPTY-STRING---"
        },
        "photo_url": "https://www.gravatar.com/avatar/35f0aa0d90d6fdfb178a847bd5ae5e6c?d=mp",
        "details_url": null,
        "email": "curtis@noq.dev"
      }
    },
    "host": "corp_noq_dev",
    "justification": "test",
    "request_id": "[b48dabb4-6471-4388-ae09-9f6814430fd0](/policies/request/b48dabb4-6471-4388-ae09-9f6814430fd0)",
    "status": "approved",
    "principal": {
      "principal_type": "AwsResource",
      "principal_arn": "arn:aws:iam::259868150464:role/faa"
    },
    "username": "curtis@noq.dev",
    "arn": "arn:aws:iam::259868150464:role/faa",
    "request_time": 1644793721
  },
  {
    "last_updated": 1644793594,
    "version": "2",
    "extended_request": {
      "request_status": "approved",
      "cross_account": false,
      "comments": [
        {
          "user_email": "curtis@noq.dev",
          "edited": null,
          "id": "38ecfd1f-7150-440c-beaf-babe27ea122b",
          "text": "Self-approved by admin: curtis@noq.dev",
          "last_modified": "2022-02-13T23:06:29+00:00",
          "user": {
            "extended_info": {
              "name": {
                "fullName": "---DYNAMO-EMPTY-STRING---",
                "givenName": "---DYNAMO-EMPTY-STRING---",
                "familyName": "---DYNAMO-EMPTY-STRING---"
              },
              "userName": "curtis@noq.dev",
              "primaryEmail": "curtis@noq.dev",
              "domain": "---DYNAMO-EMPTY-STRING---"
            },
            "photo_url": "https://www.gravatar.com/avatar/35f0aa0d90d6fdfb178a847bd5ae5e6c?d=mp",
            "details_url": null,
            "email": "curtis@noq.dev"
          },
          "timestamp": "2022-02-13T23:06:29+00:00"
        }
      ],
      "changes": {
        "changes": [
          {
            "original_value": null,
            "original_key": null,
            "resources": [],
            "autogenerated": false,
            "change_type": "resource_tag",
            "version": "3.0",
            "principal": {
              "principal_type": "AwsResource",
              "principal_arn": "arn:aws:iam::259868150464:role/faa"
            },
            "tag_action": "create",
            "updated_by": "curtis@noq.dev",
            "id": "46720387-954f-44b8-a900-67658ee52e660",
            "value": "curtis@noq.dev",
            "key": "noq-authorized",
            "status": "applied"
          }
        ]
      },
      "approvers": [],
      "requester_email": "curtis@noq.dev",
      "reviewer": "curtis@noq.dev",
      "request_url": null,
      "principal": {
        "principal_type": "AwsResource",
        "principal_arn": "arn:aws:iam::259868150464:role/faa"
      },
      "arn_url": "---DYNAMO-EMPTY-STRING---",
      "admin_auto_approve": true,
      "id": "46720387-954f-44b8-a900-67658ee52e66",
      "justification": "Need it now!",
      "timestamp": "2022-02-13T23:06:26+00:00",
      "requester_info": {
        "extended_info": {
          "name": {
            "fullName": "---DYNAMO-EMPTY-STRING---",
            "givenName": "---DYNAMO-EMPTY-STRING---",
            "familyName": "---DYNAMO-EMPTY-STRING---"
          },
          "userName": "curtis@noq.dev",
          "primaryEmail": "curtis@noq.dev",
          "domain": "---DYNAMO-EMPTY-STRING---"
        },
        "photo_url": "https://www.gravatar.com/avatar/35f0aa0d90d6fdfb178a847bd5ae5e6c?d=mp",
        "details_url": null,
        "email": "curtis@noq.dev"
      }
    },
    "host": "corp_noq_dev",
    "justification": "Need it now!",
    "request_id": "[46720387-954f-44b8-a900-67658ee52e66](/policies/request/46720387-954f-44b8-a900-67658ee52e66)",
    "status": "approved",
    "principal": {
      "principal_type": "AwsResource",
      "principal_arn": "arn:aws:iam::259868150464:role/faa"
    },
    "username": "curtis@noq.dev",
    "arn": "arn:aws:iam::259868150464:role/faa",
    "request_time": 1644793586
  }
]} />
    </>
  )
}

export default RequestTable
