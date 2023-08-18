variable "environment" {
  description = "Environment name. Passed on as a puppet fact"
  type        = string
}

variable "gpg_public_key" {
  description = "Public GPG key used to verify signature of the InfraHouse releases repo."
  type        = string
}

variable "role" {
  description = "Puppet role. Passed on as a puppet fact"
  type        = string
}

variable "ubuntu_codename" {
  description = "Ubuntu version to use for the jumphost"
  type        = string
  default     = "jammy"
}
