variable "cancel_instance_refresh_on_error" {
  description = "If True, ih-puppet will attempt to cancel instance refreshes on an autoscaling group, this instance is a part of."
  type        = bool
  default     = false
}

variable "custom_facts" {
  description = "A map of custom puppet facts"
  type        = any
  default     = {}
}

variable "environment" {
  description = <<-EOT
    Environment name. Passed on as a puppet fact.
    Must contain only lowercase letters, numbers, and underscores (no hyphens).
  EOT
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9_]+$", var.environment))
    error_message = "environment must contain only lowercase letters, numbers, and underscores (no hyphens). Got: ${var.environment}"
  }
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
  type = map(
    object(
      {
        source   = string
        key      = string
        machine  = optional(string)
        authFrom = optional(string)
        priority = optional(number)
      }
    )
  )
  default = {}
}

variable "gzip_userdata" {
  description = "Whether compress user data or not."
  type        = bool
  default     = false
}

variable "mounts" {
  description = "List of volumes to be mounted in the instance. One list item is a list itself with values [ fs_spec, fs_file, fs_vfstype, fs_mntops, fs-freq, fs_passno ]"
  default     = []
  type        = list(list(string))
  nullable    = false
}

variable "packages" {
  description = "List of packages to install when the instances bootstraps."
  type        = list(string)
  default     = []
}

variable "pre_runcmd" {
  description = "Commands to run before runcmd"
  type        = list(string)
  default     = []
}

variable "post_runcmd" {
  description = "Commands to run after runcmd"
  type        = list(string)
  default     = []
}
variable "puppet_debug_logging" {
  description = "Enable debug logging if true."
  type        = bool
  default     = false
}

variable "puppet_environmentpath" {
  description = "A path for directory environments."
  type        = string
  default     = "{root_directory}/environments"
}

variable "puppet_hiera_config_path" {
  description = "Path to hiera configuration file."
  type        = string
  default     = "{root_directory}/environments/{environment}/hiera.yaml"
}

variable "puppet_manifest" {
  description = "Path to puppet manifest. By default ih-puppet will apply {root_directory}/environments/{environment}/manifests/site.pp."
  type        = string
  default     = null
}

variable "puppet_module_path" {
  description = "Path to common puppet modules."
  type        = string
  default     = "{root_directory}/modules"
}

variable "puppet_root_directory" {
  description = "Path where the puppet code is hosted."
  type        = string
  default     = "/opt/puppet-code"
}

variable "role" {
  description = <<-EOT
    Puppet role. Passed on as a puppet fact.
    Must contain only lowercase letters, numbers, and underscores (no hyphens).
  EOT
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9_]+$", var.role))
    error_message = "role must contain only lowercase letters, numbers, and underscores (no hyphens). Got: ${var.role}"
  }
}

variable "ssh_host_keys" {
  description = <<-EOT
    List of instance's SSH host keys. Can be rsa, ecdsa, ed25519, etc.
    See https://cloudinit.readthedocs.io/en/latest/reference/examples.html#configure-instance-s-ssh-keys
  EOT
  type = list(
    object(
      {
        type : string
        private : string
        public : string
      }
    )
  )
  default   = []
  sensitive = true
}

variable "ubuntu_codename" {
  description = <<-EOT
    Ubuntu version codename to use. Determines which InfraHouse repository to configure.
    Supported versions: focal (20.04), jammy (22.04), noble (24.04), oracular (24.10)
    Note: Some versions may require additional GPG fingerprints in bootcmd.sh (see issue #62).
  EOT
  type        = string
  default     = "jammy"

  validation {
    condition     = contains(["focal", "jammy", "noble", "oracular"], var.ubuntu_codename)
    error_message = "ubuntu_codename must be one of: focal, jammy, noble, oracular. Got: ${var.ubuntu_codename}"
  }
}
