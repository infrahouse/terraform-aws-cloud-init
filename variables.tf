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
  description = <<-EOT
    Additional APT repositories to configure on an instance.

    Each repository requires:
    - source: APT source line (e.g., "deb [signed-by=$KEY_FILE] https://example.com/ubuntu jammy main")

    Key options (use ONE of the following):
    - key: (optional) GPG public key for the repository (PEM format)
    - keyid: (optional) GPG key ID or fingerprint to import from a keyserver
    - keyserver: (optional) Keyserver URL to fetch keyid from (default: keyserver.ubuntu.com)

    Note: Either 'key' OR 'keyid' must be provided. If using 'keyid', you can optionally
    specify a custom 'keyserver'. Using 'keyid' reduces userdata size by ~3KB per repository
    (GPG keys are typically 3-5KB, while a keyid is ~50 bytes). This is important because
    AWS limits userdata to 16KB compressed, so embedded keys can quickly exhaust this limit.

    Authentication options:
    - machine: (optional) Hostname for APT authentication (e.g., "apt.example.com")
    - authFrom: (optional) ARN of AWS Secrets Manager secret containing credentials

    Note: machine and authFrom must be both set or both unset for authentication to work.

    Other options:
    - priority: (optional) APT preference priority (1-1000)

    Example with embedded key:
    extra_repos = {
      "my-repo" = {
        source   = "deb [signed-by=$KEY_FILE] https://apt.example.com/ubuntu jammy main"
        key      = "-----BEGIN PGP PUBLIC KEY BLOCK-----\n...\n-----END PGP PUBLIC KEY BLOCK-----"
        machine  = "apt.example.com"
        authFrom = "arn:aws:secretsmanager:us-west-2:123456789012:secret:apt-credentials"
        priority = 500
      }
    }

    Example with keyid (recommended to save userdata space):
    extra_repos = {
      "my-repo" = {
        source    = "deb [signed-by=$KEY_FILE] https://apt.example.com/ubuntu noble main"
        keyid     = "A627B7760019BA51B903453D37A181B689AD619"
        keyserver = "keyserver.ubuntu.com"  # optional, this is the default
      }
    }
  EOT
  type = map(
    object(
      {
        source    = string
        key       = optional(string)
        keyid     = optional(string)
        keyserver = optional(string)
        machine   = optional(string)
        authFrom  = optional(string)
        priority  = optional(number)
      }
    )
  )
  default = {}

  validation {
    condition = alltrue([
      for name, repo in var.extra_repos :
      (repo.machine == null && repo.authFrom == null) ? true : (repo.machine != null && repo.authFrom != null)
    ])
    error_message = <<-EOT
      extra_repos: machine and authFrom must be both set or both unset.
      If you need APT authentication, provide both machine (hostname) and authFrom (secret ARN).
    EOT
  }

  validation {
    condition = alltrue([
      for name, repo in var.extra_repos :
      repo.priority == null ? true : (repo.priority >= 1 && repo.priority <= 1000)
    ])
    error_message = "extra_repos.priority must be between 1 and 1000 if specified"
  }

  validation {
    condition = alltrue([
      for name, repo in var.extra_repos :
      can(regex("https?://[a-zA-Z0-9][a-zA-Z0-9.-]+[a-zA-Z0-9]", repo.source))
    ])
    error_message = "extra_repos.source must contain a valid HTTP or HTTPS URL with a proper hostname"
  }

  validation {
    condition = alltrue([
      for name, repo in var.extra_repos :
      (repo.key != null && repo.keyid == null) || (repo.key == null && repo.keyid != null)
    ])
    error_message = <<-EOT
      extra_repos: exactly one of 'key' or 'keyid' must be provided for each repository.
      Use 'key' to embed the full GPG key, or 'keyid' to fetch from a keyserver.
    EOT
  }

  validation {
    condition = alltrue([
      for name, repo in var.extra_repos :
      repo.keyserver == null ? true : repo.keyid != null
    ])
    error_message = "extra_repos: 'keyserver' can only be specified when 'keyid' is provided"
  }

  validation {
    condition = alltrue([
      for name, repo in var.extra_repos :
      repo.keyid == null ? true : can(regex("^[A-Fa-f0-9 ]+$", repo.keyid))
    ])
    error_message = "extra_repos: 'keyid' must be a valid hexadecimal string (GPG key ID or fingerprint, spaces allowed)"
  }
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

    Currently supported: noble (24.04 LTS)

    Support Policy: This module supports current Ubuntu LTS releases only.
    - noble (24.04) is supported until April 2029 (standard support EOL)
    - When plucky (26.04) releases in April 2026, both noble and plucky will be supported
    - Previous LTS versions (jammy, focal) are no longer supported due to expired GPG keys

    Note: Non-LTS releases (like oracular) are not supported due to short 9-month lifecycles.
  EOT
  type        = string
  default     = "noble"

  validation {
    condition     = contains(["noble"], var.ubuntu_codename)
    error_message = "ubuntu_codename must be: noble. Previous versions (jammy, focal) have expired GPG keys. Got: ${var.ubuntu_codename}"
  }
}
