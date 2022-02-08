import tornado.escape

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.auth import can_admin_all
from common.models import WebResponse


class ConfigHandler(BaseHandler):
    async def get(self):
        """"""
        host = self.ctx.host
        if not can_admin_all(self.user, self.groups, host):
            self.set_status(403)
            return
        external_id = config.get_host_specific_key("tenant_details.external_id", host)
        if not external_id:
            self.set_status(400)
            res = WebResponse(status_code=400, message="External ID not found")
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return
        noq_cluster_role = config.get("_global_.integrations.aws.node_role", host)
        central_role_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": noq_cluster_role},
                    "Condition": {"StringEquals": {"sts:ExternalId": external_id}},
                    "Action": ["sts:AssumeRole", "sts:TagSession"],
                }
            ],
        }

        central_role_inline_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "access-analyzer:*",
                        "cloudtrail:*",
                        "cloudwatch:*",
                        "config:SelectResourceConfig",
                        "config:SelectAggregateResourceConfig",
                        "dynamodb:batchgetitem",
                        "dynamodb:batchwriteitem",
                        "dynamodb:deleteitem",
                        "dynamodb:describe*",
                        "dynamodb:getitem",
                        "dynamodb:getrecords",
                        "dynamodb:getsharditerator",
                        "dynamodb:putitem",
                        "dynamodb:query",
                        "dynamodb:scan",
                        "dynamodb:updateitem",
                        "dynamodb:CreateTable",
                        "dynamodb:UpdateTimeToLive",
                        "sns:createplatformapplication",
                        "sns:createplatformendpoint",
                        "sns:deleteendpoint",
                        "sns:deleteplatformapplication",
                        "sns:getendpointattributes",
                        "sns:getplatformapplicationattributes",
                        "sns:listendpointsbyplatformapplication",
                        "sns:publish",
                        "sns:setendpointattributes",
                        "sns:setplatformapplicationattributes",
                        "sts:assumerole",
                    ],
                    "Resource": "*",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "autoscaling:Describe*",
                        "cloudwatch:Get*",
                        "cloudwatch:List*",
                        "config:BatchGet*",
                        "config:List*",
                        "config:Select*",
                        "ec2:DescribeSubnets",
                        "ec2:describevpcendpoints",
                        "ec2:DescribeVpcs",
                        "iam:GetAccountAuthorizationDetails",
                        "iam:ListAccountAliases",
                        "iam:ListAttachedRolePolicies",
                        "ec2:describeregions",
                        "s3:GetBucketPolicy",
                        "s3:GetBucketTagging",
                        "s3:ListAllMyBuckets",
                        "s3:ListBucket",
                        "s3:PutBucketPolicy",
                        "s3:PutBucketTagging",
                        "sns:GetTopicAttributes",
                        "sns:ListTagsForResource",
                        "sns:ListTopics",
                        "sns:SetTopicAttributes",
                        "sns:TagResource",
                        "sns:UnTagResource",
                        "sqs:GetQueueAttributes",
                        "sqs:GetQueueUrl",
                        "sqs:ListQueues",
                        "sqs:ListQueueTags",
                        "sqs:SetQueueAttributes",
                        "sqs:TagQueue",
                        "sqs:UntagQueue",
                    ],
                    "Resource": "*",
                },
            ],
        }
        spoke_role_inline_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "autoscaling:Describe*",
                        "cloudwatch:Get*",
                        "cloudwatch:List*",
                        "config:BatchGet*",
                        "config:List*",
                        "config:Select*",
                        "ec2:describeregions",
                        "ec2:DescribeSubnets",
                        "ec2:describevpcendpoints",
                        "ec2:DescribeVpcs",
                        "iam:*",
                        "s3:GetBucketPolicy",
                        "s3:GetBucketTagging",
                        "s3:ListAllMyBuckets",
                        "s3:ListBucket",
                        "s3:PutBucketPolicy",
                        "s3:PutBucketTagging",
                        "sns:GetTopicAttributes",
                        "sns:ListTagsForResource",
                        "sns:ListTopics",
                        "sns:SetTopicAttributes",
                        "sns:TagResource",
                        "sns:UnTagResource",
                        "sqs:GetQueueAttributes",
                        "sqs:GetQueueUrl",
                        "sqs:ListQueues",
                        "sqs:ListQueueTags",
                        "sqs:SetQueueAttributes",
                        "sqs:TagQueue",
                        "sqs:UntagQueue",
                    ],
                    "Resource": "*",
                }
            ],
        }

        config_to_return = {
            "aws": {
                "external_id": config.get_host_specific_key(
                    "tenant_details.external_id", host
                ),
                "cluster_role": noq_cluster_role,
                "spoke_role_name": config.get_host_specific_key(
                    "policies.role_name", host
                ),
                "central_role_name": config.get("_global_.integrations.aws.central_role_name", "NoqCentralRole"),
                "central_role_trust_policy": central_role_trust_policy,
                "central_role_inline_policy": central_role_inline_policy,
                "spoke_role_inline_policy": spoke_role_inline_policy,
            },
        }

        pre_role_arns_to_assume = config.get_host_specific_key(
            "policies.pre_role_arns_to_assume", host, []
        )
        if pre_role_arns_to_assume:
            config_to_return["aws"]["central_role_arn"] = pre_role_arns_to_assume[-1][
                "role_arn"
            ]

            config_to_return["aws"]["spoke_role_trust_policy"] = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": config_to_return["aws"]["central_role_arn"]
                        },
                        "Action": ["sts:AssumeRole", "sts:TagSession"],
                    }
                ],
            }

        self.write(config_to_return)

    async def post(self):
        """
        Write configuration
        """
        host = self.ctx.host
        if not can_admin_all(self.user, self.groups, host):
            self.set_status(403)
            return
        # TODO: Format data into a model
        data = tornado.escape.json_decode(self.request.body)
        valid_commands = [
            "update_central_role",
            "remove_central_role",
            "add_spoke_account",
            "remove_spoke_account",
        ]
        if data.get("command") not in valid_commands:
            self.set_status(400)
            return
        if data.get("command") == "update_central_role":
            # Attempt to assume role with external ID
            # external_id = config.get_host_specific_key(
            #     "tenant_details.external_id", host
            # )

            pass
        if data.get("command") == "add_spoke_account":
            pass
        self.set_status(200)
