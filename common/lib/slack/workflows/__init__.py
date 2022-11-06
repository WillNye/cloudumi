import json

request_permissions_to_resource_block = None # TODO

request_access_to_resource_block = json.loads("""
                                              {
	"type": "modal",
	"callback_id": "request_access_to_resource",
	"title": {
		"type": "plain_text",
		"text": "Noq",
		"emoji": true
	},
	"submit": {
		"type": "plain_text",
		"text": "Submit Request",
		"emoji": true
	},
	"close": {
		"type": "plain_text",
		"text": "Cancel",
		"emoji": true
	},
	"blocks": [
		{
			"type": "section",
			"block_id": "request_access",
			"text": {
				"type": "mrkdwn",
				"text": "Request Access to one or more roles"
			},
			"accessory": {
				"action_id": "select_resources",
				"type": "multi_external_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Select resources"
				},
				"min_query_length": 3
			}
		},
		{
			"type": "input",
			"element": {
				"type": "static_select",
				"options": [
					{
						"text": {
							"type": "plain_text",
							"text": "1 Hour",
							"emoji": true
						},
						"value": "1h"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "2 Hours",
							"emoji": true
						},
						"value": "2h"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "4 Hours",
							"emoji": true
						},
						"value": "4h"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "8 Hours",
							"emoji": true
						},
						"value": "8h"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "24 Hours",
							"emoji": true
						},
						"value": "24h"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Never",
							"emoji": true
						},
						"value": "no_expire"
					}
				],
				"action_id": "static_select-action"
			},
			"label": {
				"type": "plain_text",
				"text": "Expiration",
				"emoji": true
			}
		},
		{
			"type": "input",
			"element": {
				"type": "plain_text_input",
				"multiline": true,
				"action_id": "plain_text_input-action",
				"placeholder": {
					"type": "plain_text",
					"text": "I need access for..."
				}
			},
			"label": {
				"type": "plain_text",
				"text": "Justification",
				"emoji": true
			}
		}
	]
}
""")


remove_unused_identities_sample = [
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "Cloud identities associated with your team have not been used in the past 180 days. Please review these identities and let us know which action to take.",
				"emoji": True
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "<fakeLink.toNoqRole.com|prod: role/LemurApp> "
			},
			"accessory": {
				"type": "static_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Ignore (Do not Delete)",
					"emoji": True
				},
				"options": [
					{
						"text": {
							"type": "plain_text",
							"text": "Ignore Forever (Do not Delete)",
							"emoji": True
						},
						"value": "ignore"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Delete Immediately",
							"emoji": True
						},
						"value": "delete"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Re-assign to a different team",
							"emoji": True
						},
						"value": "reassign"
					}
				],
				"action_id": "static_select-action"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "<fakeLink.toNoqRole.com|test: role/teleport> "
			},
			"accessory": {
				"type": "static_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Ignore (Do not Delete)",
					"emoji": True
				},
				"options": [
					{
						"text": {
							"type": "plain_text",
							"text": "Ignore Forever (Do not Delete)",
							"emoji": True
						},
						"value": "ignore"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Delete Immediately",
							"emoji": True
						},
						"value": "delete"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Re-assign to a different team",
							"emoji": True
						},
						"value": "reassign"
					}
				],
				"action_id": "static_select-action"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "<fakeLink.toNoqRole.com|staging: role/Nonerole> "
			},
			"accessory": {
				"type": "static_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Ignore (Do not Delete)",
					"emoji": True
				},
				"options": [
					{
						"text": {
							"type": "plain_text",
							"text": "Ignore Forever (Do not Delete)",
							"emoji": True
						},
						"value": "ignore"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Delete Immediately",
							"emoji": True
						},
						"value": "delete"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Re-assign to a different team",
							"emoji": True
						},
						"value": "reassign"
					}
				],
				"action_id": "static_select-action"
			}
		},
  {
			"type": "divider"
		},
		{
			"type": "actions",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "Submit",
						"emoji": True
					},
					"value": "submit",
					"action_id": "submit"
				}
			]
		}
	]

unauthorized_change_sample = [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "An unauthorized Cloud Identity Modification was detected and automatically remediated.\n\n*<fakeLink.toEmployeeProfile.com|Click here to view CloudTrail Logs>*"
			}
		},
		{
			"type": "section",
			"fields": [
				{
					"type": "mrkdwn",
					"text": "*Identity:*\t<fakeLink.toNoqRole.com|arn:aws:iam::759357822767:role/effective_permissions_demo_role>"
				},
				{
					"type": "mrkdwn",
					"text": "*Action:*\tiam:attachrolepolicy"
				},
				{
					"type": "mrkdwn",
					"text": "*Actor:*\t<fakeLink.toNoqRole.com|arn:aws:iam::759357822767:role/prod_admin>"
				},
				{
					"type": "mrkdwn",
					"text": "*Policy Details:*\t<fakeLink.toPolicy.com|arn:aws:iam::aws:policy/AdministratorAccess>"
				},
				{
					"type": "mrkdwn",
					"text": "*Session Name:*\tcurtis@noq.dev"
				}
			]
		},
		{
			"type": "actions",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"emoji": True,
						"text": "Approve and Submit Request"
					},
					"style": "primary",
					"value": "click_me_123"
				},
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"emoji": True,
						"text": "Ignore"
					},
					"style": "danger",
					"value": "click_me_123"
				}
			]
		}
	]


request_access_to_resource_success = json.loads("""{
	"type": "modal",
	"title": {
		"type": "plain_text",
		"text": "Noq",
		"emoji": true
	},
	"close": {
		"type": "plain_text",
		"text": "Close",
		"emoji": true
	},
	"blocks": [
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "Sucess!",
				"emoji": true
			}
		}
	]
}""")