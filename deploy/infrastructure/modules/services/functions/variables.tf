variable "runtime" {
  default = "python3.9"
}

variable "registration_response_queue" {
  description = "The registration response queue"
  type = string
}