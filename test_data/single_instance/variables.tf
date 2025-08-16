variable "region" {}
variable "role_arn" {
  default = null
}
variable "ami_vendor" {
  description = "Whether ubuntu or infrahouse"
}

variable "subnet_id" {}
