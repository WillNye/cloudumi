output "notifications_sender_identity" {
  description = "ARN of the notifications sender identity"
  value       = aws_ses_email_identity.notifications_sender_identity.arn
}
