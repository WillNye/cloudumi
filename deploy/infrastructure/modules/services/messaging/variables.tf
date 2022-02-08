variable "account_id" {
  description = "The account id that this infrastructure is built in"
  type        = string
}

variable "cluster_id" {
  type        = string
  description = "The cluster ID for CloudUmi."
}

variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}