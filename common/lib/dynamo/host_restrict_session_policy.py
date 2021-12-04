import ujson as json


def get_session_policy_for_host(host):
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
                            "dynamodb:LeadingKeys": [f"{host}"]
                        }
                    },
                }
            ],
        }
    )
