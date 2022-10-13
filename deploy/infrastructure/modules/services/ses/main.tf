resource "aws_ses_email_identity" "notifications" {
  email = "notifications@noq.dev"
}

resource "aws_ses_domain_mail_from" "notifications" {
  domain           = aws_ses_email_identity.notifications.email
  mail_from_domain = var.notifications_mail_from_domain
}
