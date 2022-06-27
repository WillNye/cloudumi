import common.lib.noq_json as json


def get_session_policy_for_tenant(tenant):
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["dynamodb:*"],
                    "Resource": ["*"],
                    "Condition": {
                        "ForAllValues:StringEquals": {
                            "dynamodb:LeadingKeys": [f"{tenant}"]
                        }
                    },
                }
            ],
        }
    )
