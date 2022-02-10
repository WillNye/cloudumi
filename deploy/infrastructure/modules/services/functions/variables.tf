variable "account_id" {
  description = "The account id that this infrastructure is built in"
  type        = string
}

variable "region" {
  type    = string
  default = "us-west-2"

  validation {
    condition     = contains(["us-west-1", "us-west-2"], var.region)
    error_message = "Allowed values for input_parameter are \"us-west-1\", \"us-west-2\"."
  }
}

variable "registration_response_queue" {
  description = "The registration response queue"
  type        = string
}

variable "runtime" {
  default = "python3.9"
}