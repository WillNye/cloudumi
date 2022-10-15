resource "aws_ses_email_identity" "notifications" {
  email = "notifications@noq.dev"
}

resource "aws_ses_domain_mail_from" "notifications" {
  domain           = aws_ses_email_identity.notifications.email
  mail_from_domain = var.notifications_mail_from_domain
}

data "aws_iam_policy_document" "deny-external" {
  statement {
    sid       = "DenyExternal"
    actions   = ["SES:SendEmail", "SES:SendRawEmail"]
    resources = [aws_ses_email_identity.notifications.arn]
    effect    = "Deny"
    principals {
      identifiers = ["*"]
      type        = "*"
    }
    condition {
      test     = "ForAnyValue:StringNotLike"
      variable = "ses:Recipients"

      values = [
        "*@noq.dev",
        # From Cognito-to-SES, it seems it is injecting some hidden amazonses specific email address
        "*@*.amazonses.com",
      ]
    }
  }
}

resource "aws_ses_identity_policy" "DenyExternal" {
  # If it's not prod enivronment, then atach DenyExternal policy
  count    = var.tags["Environment"] != "production" ? 1 : 0
  identity = aws_ses_email_identity.notifications.arn
  name     = "DenyExternal"
  policy   = data.aws_iam_policy_document.deny-external.json
}
