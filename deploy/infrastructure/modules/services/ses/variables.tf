variable "notifications_mail_from_domain" {
  description = "Messages sent through Amazon SES will be marked as originating from noq.dev domain"
  type        = string
}

variable "tags" {
  description = "map of tags"
  type        = map(any)
}