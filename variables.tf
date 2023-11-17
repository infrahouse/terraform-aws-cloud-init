variable "environment" {
  description = "Environment name. Passed on as a puppet fact."
  type        = string
}

variable "extra_files" {
  description = "Additional files to create on an instance."
  type = list(object({
    content     = string
    path        = string
    permissions = string
  }))
  default = []
}

variable "extra_repos" {
  description = "Additional APT repositories to configure on an instance."
  type = map(object({
    source = string
    key    = string
  }))
  default = {}
}
variable "packages" {
  description = "List of packages to install when the instances bootstraps."
  type        = list(string)
  default     = []
}

variable "puppet_debug_logging" {
  description = "Enable debug logging if true."
  type        = bool
  default     = false
}

variable "puppet_hiera_config_path" {
  description = "Path to hiera configuration file."
  default     = "{root_directory}/environments/{environment}/hiera.yaml"
}

variable "puppet_module_path" {
  description = "Path to common puppet modules."
  default     = "{root_directory}/modules"
}

variable "puppet_root_directory" {
  description = "Path where the puppet code is hosted."
  default     = "/opt/puppet-code"
}

variable "role" {
  description = "Puppet role. Passed on as a puppet fact."
  type        = string
}

variable "ubuntu_codename" {
  description = "Ubuntu version to use for the jumphost."
  type        = string
  default     = "jammy"
}
