from unittest.mock import MagicMock, mock_open, patch

import pytest
import ujson as json
from deepdiff import DeepDiff

from util.tests.fixtures.globals import tenant
from util.tests.fixtures.util import ConsoleMeAsyncHTTPTestCase


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("sqs")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("sts")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("dynamodb")
class TestRequestsHandler(ConsoleMeAsyncHTTPTestCase):
    def get_app(self):
        from common.config import config

        self.config = config

        from common.lib.notifications import smtplib

        smtplib.SMTP_SSL = MagicMock()

        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        # Method not allowed
        headers = {
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }
        response = self.fetch("/api/v2/requests", method="GET", headers=headers)
        self.assertEqual(response.code, 405)

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("populate_caches")
    def test_requestshandler_post(self):
        mock_request_data = [
            {
                "request_id": 12345,
                "username": "user@example.com",
                "request_time": 22345,
            },
            {
                "request_id": 12346,
                "username": "userb@example.com",
                "request_time": 12345,
            },
        ]

        expected_response = {
            "totalCount": 2,
            "filteredCount": 2,
            "data": mock_request_data,
        }

        headers = {
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/requests", method="POST", headers=headers, body="{}"
        )
        self.assertEqual(response.code, 200)
        diff = DeepDiff(json.loads(response.body), expected_response)
        self.assertFalse(diff)

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("dynamodb")
    @pytest.mark.usefixtures("populate_caches")
    def test_post_request(self):
        mock_request_data = {
            "justification": "test asdf",
            "admin_auto_approve": False,
            "changes": {
                "changes": [
                    {
                        "principal": {
                            "principal_arn": "arn:aws:iam::123456789012:role/TestInstanceProfile",
                            "principal_type": "AwsResource",
                        },
                        "change_type": "inline_policy",
                        "action": "attach",
                        "policy": {
                            "policy_document": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Action": ["sqs:SetQueueAttributes"],
                                        "Effect": "Allow",
                                        "Resource": [
                                            "arn:aws:sqs:us-east-1:223456789012:queue"
                                        ],
                                    }
                                ],
                            }
                        },
                    }
                ]
            },
        }

        headers = {
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/request",
            method="POST",
            headers=headers,
            body=json.dumps(mock_request_data),
        )
        self.assertEqual(response.code, 200)
        response_d = json.loads(response.body)
        self.assertEqual(response_d["errors"], 0)
        self.assertEqual(response_d["request_created"], True)
        self.assertIn("/policies/request/", response_d["request_url"])

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("populate_caches")
    def test_post_request_admin_auto_approve(self):
        mock_request_data = {
            "justification": "test asdf",
            "admin_auto_approve": True,
            "changes": {
                "changes": [
                    {
                        "principal": {
                            "principal_arn": "arn:aws:iam::123456789012:role/TestInstanceProfile",
                            "principal_type": "AwsResource",
                        },
                        "change_type": "inline_policy",
                        "action": "attach",
                        "policy": {
                            "policy_document": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Action": ["sqs:SetQueueAttributes"],
                                        "Effect": "Allow",
                                        "Resource": [
                                            "arn:aws:sqs:us-east-1:223456789012:queue"
                                        ],
                                    }
                                ],
                            }
                        },
                    }
                ]
            },
        }

        response = self.fetch(
            "/api/v2/request",
            method="POST",
            body=json.dumps(mock_request_data),
            user="consoleme_admins@example.com",
        )
        self.assertEqual(response.code, 200)
        response_d = json.loads(response.body)
        self.assertEqual(response_d["errors"], 0)
        self.assertEqual(response_d["request_created"], True)
        self.assertIn("/policies/request/", response_d["request_url"])
        self.assertIn(
            {"status": "success", "message": "Successfully updated request status"},
            response_d["action_results"],
        )
        self.assertIn(
            {"status": "success", "message": "Successfully updated change in dynamo"},
            response_d["action_results"],
        )

    @pytest.mark.skip(reason="EN-637")
    def test_post_limit(self):
        # mock_request_data = [
        #     {"request_id": 12345, "username": "user@example.com"},
        #     {"request_id": 12346, "username": "userb@example.com"},
        # ]

        response = self.fetch(
            "/api/v2/requests",
            method="POST",
            body=json.dumps({"limit": 1}),
        )
        self.assertEqual(response.code, 200)
        self.assertEqual(len(json.loads(response.body)), 3)
        self.assertEqual(len(json.loads(response.body)["data"]), 1)

    @pytest.mark.skip(reason="EN-637")
    def test_post_filter(self):
        mock_request_data = [
            {"request_id": 12345, "username": "user@example.com"},
            {"request_id": 12346, "username": "userb@example.com"},
        ]

        response = self.fetch(
            "/api/v2/requests",
            method="POST",
            body=json.dumps({"filters": {"request_id": "12346"}}),
        )
        self.assertEqual(response.code, 200)
        res = json.loads(response.body)
        self.assertEqual(len(json.loads(response.body)), 3)
        self.assertEqual(len(json.loads(response.body)["data"]), 1)
        self.assertEqual(res["data"][0], mock_request_data[1])

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("populate_caches")
    def test_post_new_managed_policy_resource_request(self):
        headers = {
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }

        input_body = {
            "admin_auto_approve": False,
            "justification": "Test justification",
            "changes": {
                "changes": [
                    {
                        "principal": {
                            "principal_type": "AwsResource",
                            "principal_arn": "arn:aws:iam::123456789012:policy/testpolicy",
                        },
                        "change_type": "managed_policy_resource",
                        "new": True,
                        "action": "update",
                        "policy": {
                            "policy_document": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Action": [
                                            "s3:GetObjectVersionTagging",
                                            "s3:GetObjectAcl",
                                            "s3:ListBucket",
                                            "s3:GetObject",
                                            "s3:GetObjectVersionAcl",
                                            "s3:GetObjectTagging",
                                            "s3:GetObjectVersion",
                                            "s3:ListBucketVersions",
                                        ],
                                        "Effect": "Allow",
                                        "Resource": [
                                            "arn:aws:s3:::12345",
                                            "arn:aws:s3:::12345/*",
                                        ],
                                    }
                                ],
                            }
                        },
                    }
                ]
            },
        }
        response = self.fetch(
            "/api/v2/request",
            method="POST",
            headers=headers,
            body=json.dumps(input_body),
        )
        result = json.loads(response.body)
        result.pop("request_id")
        result.pop("request_url")
        result["extended_request"].pop("id")
        result["extended_request"].pop("timestamp")
        result["extended_request"]["changes"]["changes"][0].pop("id")
        self.assertEqual(
            result,
            {
                "errors": 0,
                "request_created": True,
                "action_results": [],
                "extended_request": {
                    "request_url": None,
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:policy/testpolicy",
                    },
                    "justification": "Test justification",
                    "requester_email": "testuser@example.com",
                    "approvers": [],
                    "request_status": "pending",
                    "cross_account": False,
                    "arn_url": "/policies/edit/123456789012/managed_policy/testpolicy",
                    "admin_auto_approve": False,
                    "changes": {
                        "changes": [
                            {
                                "principal": {
                                    "principal_type": "AwsResource",
                                    "principal_arn": "arn:aws:iam::123456789012:policy/testpolicy",
                                },
                                "change_type": "managed_policy_resource",
                                "resources": [],
                                "version": "3.0",
                                "status": "not_applied",
                                "autogenerated": False,
                                "updated_by": None,
                                "new": True,
                                "policy": {
                                    "version": None,
                                    "policy_document": {
                                        "Version": "2012-10-17",
                                        "Statement": [
                                            {
                                                "Action": [
                                                    "s3:GetObjectVersionTagging",
                                                    "s3:GetObjectAcl",
                                                    "s3:ListBucket",
                                                    "s3:GetObject",
                                                    "s3:GetObjectVersionAcl",
                                                    "s3:GetObjectTagging",
                                                    "s3:GetObjectVersion",
                                                    "s3:ListBucketVersions",
                                                ],
                                                "Effect": "Allow",
                                                "Resource": [
                                                    "arn:aws:s3:::12345",
                                                    "arn:aws:s3:::12345/*",
                                                ],
                                            }
                                        ],
                                    },
                                    "policy_sha256": None,
                                },
                                "old_policy": None,
                            }
                        ]
                    },
                    "requester_info": {
                        "email": "testuser@example.com",
                        "extended_info": {
                            "domain": "",
                            "userName": "testuser@example.com",
                            "name": {"givenName": "", "familyName": "", "fullName": ""},
                            "primaryEmail": "testuser@example.com",
                        },
                        "details_url": None,
                        "photo_url": "https://www.gravatar.com/avatar/7ec7606c46a14a7ef514d1f1f9038823?d=mp",
                    },
                    "reviewer": None,
                    "expiration_date": None,
                    "comments": [],
                },
            },
        )

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("populate_caches")
    def test_post_new_managed_policy_resource_request_autoapprove(self):
        user = "consoleme_admins@example.com"

        input_body = {
            "admin_auto_approve": True,
            "justification": "Unit-test",
            "changes": {
                "changes": [
                    {
                        "principal": {
                            "principal_type": "AwsResource",
                            "principal_arn": "arn:aws:iam::123456789012:policy/randompath/extra/testpolicy",
                        },
                        "change_type": "managed_policy_resource",
                        "new": True,
                        "action": "update",
                        "policy": {
                            "policy_document": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Action": [
                                            "s3:GetObjectVersionTagging",
                                            "s3:GetObjectAcl",
                                            "s3:ListBucket",
                                            "s3:GetObject",
                                            "s3:GetObjectVersionAcl",
                                            "s3:GetObjectTagging",
                                            "s3:GetObjectVersion",
                                            "s3:ListBucketVersions",
                                        ],
                                        "Effect": "Allow",
                                        "Resource": [
                                            "arn:aws:s3:::12345",
                                            "arn:aws:s3:::12345/*",
                                        ],
                                    }
                                ],
                            }
                        },
                    }
                ]
            },
        }
        response = self.fetch(
            "/api/v2/request",
            method="POST",
            body=json.dumps(input_body),
            user=user,
        )
        result = json.loads(response.body)
        result.pop("request_id")
        result.pop("request_url")
        result["extended_request"].pop("id")
        result["extended_request"].pop("timestamp")
        result["extended_request"]["changes"]["changes"][0].pop("id")
        result["extended_request"].pop("comments")
        self.assertEqual(
            result,
            {
                "errors": 0,
                "request_created": True,
                "action_results": [
                    {
                        "status": "success",
                        "message": "Successfully created managed policy arn:aws:iam::123456789012:policy/randompath/extra/testpolicy",
                    },
                    {
                        "status": "success",
                        "message": "Successfully updated change in dynamo",
                    },
                    {
                        "status": "success",
                        "message": "Successfully updated request status",
                    },
                ],
                "extended_request": {
                    "request_url": None,
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:policy/randompath/extra/testpolicy",
                    },
                    "justification": None,
                    "requester_email": "consoleme_admins@example.com",
                    "approvers": [],
                    "request_status": "approved",
                    "cross_account": False,
                    "arn_url": "/policies/edit/123456789012/managed_policy/randompath/extra/testpolicy",
                    "admin_auto_approve": True,
                    "changes": {
                        "changes": [
                            {
                                "principal": {
                                    "principal_type": "AwsResource",
                                    "principal_arn": "arn:aws:iam::123456789012:policy/randompath/extra/testpolicy",
                                },
                                "change_type": "managed_policy_resource",
                                "resources": [],
                                "version": "3.0",
                                "status": "applied",
                                "autogenerated": False,
                                "updated_by": "consoleme_admins@example.com",
                                "new": True,
                                "policy": {
                                    "version": None,
                                    "policy_document": {
                                        "Version": "2012-10-17",
                                        "Statement": [
                                            {
                                                "Action": [
                                                    "s3:GetObjectVersionTagging",
                                                    "s3:GetObjectAcl",
                                                    "s3:ListBucket",
                                                    "s3:GetObject",
                                                    "s3:GetObjectVersionAcl",
                                                    "s3:GetObjectTagging",
                                                    "s3:GetObjectVersion",
                                                    "s3:ListBucketVersions",
                                                ],
                                                "Effect": "Allow",
                                                "Resource": [
                                                    "arn:aws:s3:::12345",
                                                    "arn:aws:s3:::12345/*",
                                                ],
                                            }
                                        ],
                                    },
                                    "policy_sha256": None,
                                },
                                "old_policy": None,
                            }
                        ]
                    },
                    "requester_info": {
                        "email": "consoleme_admins@example.com",
                        "extended_info": {
                            "domain": "",
                            "userName": "consoleme_admins@example.com",
                            "name": {"givenName": "", "familyName": "", "fullName": ""},
                            "primaryEmail": "consoleme_admins@example.com",
                        },
                        "details_url": None,
                        "photo_url": "https://www.gravatar.com/avatar/ec2ee26a6397f686011678e50aeb4e81?d=mp",
                    },
                    "reviewer": "consoleme_admins@example.com",
                    "expiration_date": None,
                },
            },
        )

    def test_post_iam_role_request_dry_run(self):
        input_body = {
            "dry_run": True,
            "changes": {
                "changes": [
                    {
                        "principal": {
                            "principal_type": "AwsResource",
                            "principal_arn": "arn:aws:iam::123456789012:role/RoleNumber1",
                        },
                        "change_type": "inline_policy",
                        "action": "attach",
                        "policy": {
                            "policy_document": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Action": ["sqs:*"],
                                        "Effect": "Allow",
                                        "Resource": ["*"],
                                    }
                                ],
                            }
                        },
                    }
                ]
            },
        }
        response = self.fetch(
            "/api/v2/request",
            method="POST",
            body=json.dumps(input_body),
        )
        result = json.loads(response.body)
        result["extended_request"].pop("id")
        result["extended_request"].pop("timestamp")
        result["extended_request"]["changes"]["changes"][0].pop("id")
        result["extended_request"]["changes"]["changes"][0].pop("policy_name")

        self.assertEqual(
            result,
            {
                "errors": 0,
                "request_created": False,
                "request_id": None,
                "request_url": None,
                "action_results": None,
                "extended_request": {
                    "request_url": None,
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/RoleNumber1",
                    },
                    "justification": None,
                    "requester_email": "testuser@example.com",
                    "approvers": [],
                    "request_status": "pending",
                    "cross_account": False,
                    "arn_url": "/policies/edit/123456789012/iamrole/RoleNumber1",
                    "admin_auto_approve": False,
                    "changes": {
                        "changes": [
                            {
                                "principal": {
                                    "principal_type": "AwsResource",
                                    "principal_arn": "arn:aws:iam::123456789012:role/RoleNumber1",
                                },
                                "change_type": "inline_policy",
                                "cli_command": None,
                                "resources": [],
                                "version": "3.0",
                                "status": "not_applied",
                                "autogenerated": False,
                                "updated_by": None,
                                "read_only": False,
                                "new": True,
                                "action": "attach",
                                "python_script": None,
                                "policy": {
                                    "version": None,
                                    "policy_document": {
                                        "Version": "2012-10-17",
                                        "Statement": [
                                            {
                                                "Action": ["sqs:*"],
                                                "Effect": "Allow",
                                                "Resource": ["*"],
                                            }
                                        ],
                                    },
                                    "policy_sha256": None,
                                },
                                "old_policy": None,
                            }
                        ]
                    },
                    "requester_info": {
                        "email": "testuser@example.com",
                        "extended_info": {
                            "domain": "",
                            "userName": "testuser@example.com",
                            "name": {"givenName": "", "familyName": "", "fullName": ""},
                            "primaryEmail": "testuser@example.com",
                        },
                        "details_url": None,
                        "photo_url": "https://www.gravatar.com/avatar/7ec7606c46a14a7ef514d1f1f9038823?d=mp",
                    },
                    "reviewer": None,
                    "expiration_date": None,
                    "comments": [],
                },
            },
        )

    @pytest.mark.skip(reason="EN-637")
    @patch("git.Repo")
    @patch("git.Git")
    def test_post_honeybee_request_dry_run(self, mock_git, mock_repo):
        input_body = {
            "dry_run": True,
            "changes": {
                "changes": [
                    {
                        "principal": {
                            "principal_type": "HoneybeeAwsResourceTemplate",
                            "repository_name": "honeybee_templates",
                            "resource_identifier": "iamrole/abc.yaml",
                            "resource_url": "http://example.com/fake_repo/path/to/file.yaml",
                        },
                        "change_type": "inline_policy",
                        "action": "attach",
                        "policy": {
                            "policy_document": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Action": [
                                            "s3:GetObjectVersionTagging",
                                            "s3:GetObjectAcl",
                                            "s3:ListBucket",
                                            "s3:GetObject",
                                            "s3:GetObjectVersionAcl",
                                            "s3:GetObjectTagging",
                                            "s3:GetObjectVersion",
                                            "s3:ListBucketVersions",
                                        ],
                                        "Effect": "Allow",
                                        "Resource": [
                                            "arn:aws:s3:::bucketa",
                                            "arn:aws:s3:::bucketa/*",
                                        ],
                                        "Sid": "cmccastrapel1623864565xhwu",
                                    }
                                ],
                            }
                        },
                    }
                ]
            },
        }
        template_data = """
Policies:
  - IncludeAccounts:
      - account_a
      - account_b
      - account_c
    PolicyName: policy_a
    Statement:
      - Action:
          - '*'
        Effect: Allow
        Resource:
          - '*'
        Sid: admin"""
        with patch("builtins.open", mock_open(read_data=template_data)):
            response = self.fetch(
                "/api/v2/request",
                method="POST",
                body=json.dumps(input_body),
            )
            result = json.loads(response.body)
            result["extended_request"].pop("timestamp")
            result["extended_request"].pop("id")
            yaml_policy = result["extended_request"]["changes"]["changes"][0].pop(
                "policy"
            )
            from common.lib.yaml import yaml

            # Get this in a standard dictionary format
            generated_policy = json.loads(json.dumps(yaml.load(yaml_policy)))
            generated_policy["Policies"][1]["Statement"][0].pop("Sid")
            self.assertEqual(
                generated_policy,
                {
                    "Policies": [
                        {
                            "IncludeAccounts": ["account_a", "account_b", "account_c"],
                            "PolicyName": "policy_a",
                            "Statement": [
                                {
                                    "Action": ["*"],
                                    "Effect": "Allow",
                                    "Resource": ["*"],
                                    "Sid": "admin",
                                }
                            ],
                        },
                        {
                            "PolicyName": "self_service_generated",
                            "Statement": [
                                {
                                    "Action": [
                                        "s3:GetObjectVersionTagging",
                                        "s3:GetObjectAcl",
                                        "s3:ListBucket",
                                        "s3:GetObject",
                                        "s3:GetObjectVersionAcl",
                                        "s3:GetObjectTagging",
                                        "s3:GetObjectVersion",
                                        "s3:ListBucketVersions",
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                        "arn:aws:s3:::bucketa",
                                        "arn:aws:s3:::bucketa/*",
                                    ],
                                }
                            ],
                        },
                    ]
                },
            )
            self.assertEqual(
                result,
                {
                    "errors": 0,
                    "request_created": False,
                    "request_id": None,
                    "request_url": None,
                    "action_results": None,
                    "extended_request": {
                        "request_url": "",
                        "principal": {
                            "principal_type": "HoneybeeAwsResourceTemplate",
                            "repository_name": "honeybee_templates",
                            "resource_identifier": "iamrole/abc.yaml",
                            "resource_url": "http://example.com/fake_repo/path/to/file.yaml",
                        },
                        "justification": None,
                        "requester_email": "testuser@example.com",
                        "approvers": [],
                        "request_status": "pending",
                        "cross_account": False,
                        "arn_url": None,
                        "admin_auto_approve": False,
                        "changes": {
                            "changes": [
                                {
                                    "principal": {
                                        "principal_type": "HoneybeeAwsResourceTemplate",
                                        "repository_name": "honeybee_templates",
                                        "resource_identifier": "iamrole/abc.yaml",
                                        "resource_url": "http://example.com/fake_repo/path/to/file.yaml",
                                    },
                                    "change_type": "generic_file",
                                    "resources": [],
                                    "version": 3.0,
                                    "status": "not_applied",
                                    "id": None,
                                    "autogenerated": False,
                                    "updated_by": None,
                                    "action": "attach",
                                    "old_policy": "Policies:\n  - IncludeAccounts:\n      - account_a\n      - account_b\n      - account_c\n    PolicyName: policy_a\n    Statement:\n      - Action:\n          - '*'\n        Effect: Allow\n        Resource:\n          - '*'\n        Sid: admin\n",
                                    "encoding": "yaml",
                                }
                            ]
                        },
                        "requester_info": {
                            "email": "testuser@example.com",
                            "extended_info": {
                                "domain": "",
                                "userName": "testuser@example.com",
                                "name": {
                                    "givenName": "",
                                    "familyName": "",
                                    "fullName": "",
                                },
                                "primaryEmail": "testuser@example.com",
                            },
                            "details_url": None,
                            "photo_url": "https://www.gravatar.com/avatar/7ec7606c46a14a7ef514d1f1f9038823?d=mp",
                        },
                        "reviewer": None,
                        "expiration_date": None,
                        "comments": [],
                    },
                },
            )


class TestRequestDetailHandler(ConsoleMeAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        # expected = {
        #     "status": 501,
        #     "title": "Not Implemented",
        #     "message": "Get request details",
        # }
        # headers = {
        #     config.get_tenant_specific_key("auth.user_header_name", tenant): "user@github.com",
        #     config.get_tenant_specific_key("auth.groups_header_name", tenant): "groupa,groupb,groupc",
        # }
        # response = self.fetch(
        #     "/api/v2/requests/16fd2706-8baf-433b-82eb-8c7fada847da",
        #     method="GET",
        #     headers=headers,
        # )
        # TODO: add unit tests
        pass
        # self.assertEqual(response.code, 501)
        # self.assertDictEqual(json.loads(response.body), expected)

    def test_put(self):
        # expected = {
        #     "status": 501,
        #     "title": "Not Implemented",
        #     "message": "Update request details",
        # }
        # headers = {
        #     config.get_tenant_specific_key("auth.user_header_name", tenant): "user@github.com",
        #     config.get_tenant_specific_key("auth.groups_header_name", tenant): "groupa,groupb,groupc",
        # }
        # response = self.fetch(
        #     "/api/v2/requests/16fd2706-8baf-433b-82eb-8c7fada847da",
        #     method="PUT",
        #     headers=headers,
        #     body="{}",
        # )
        # self.assertEqual(response.code, 501)
        # self.assertDictEqual(json.loads(response.body), expected)
        # TODO: add unit tests
        pass
