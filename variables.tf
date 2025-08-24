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
  type = map(
    object(
      {
        source   = string
        key      = string
        machine  = optional(string)
        authFrom = optional(string)
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
  description = "Puppet role. Passed on as a puppet fact."
  type        = string
}

variable "ssh_host_keys" {
  description = "List of instance's SSH host keys.  Can be rsa, ecdsa, ed25519, etc. See https://cloudinit.readthedocs.io/en/latest/reference/examples.html#configure-instance-s-ssh-keys"
  type = list(
    object(
      {
        type : string
        private : string
        public : string
      }
    )
  )
  default = []
}

variable "ubuntu_codename" {
  description = "Ubuntu version to use for the jumphost."
  type        = string
  default     = "jammy"
}
