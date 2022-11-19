variable "notifications_mail_from_domain" {
  description = "Messages sent through Amazon SES will be marked as originating from noq.dev domain"
  type        = string
}

variable "notifications_sender_identity" {
  description = "The email address that will be used to identify notification origins"
  type        = string
}
variable "tags" {
  description = "map of tags"
  type        = map(any)
}
