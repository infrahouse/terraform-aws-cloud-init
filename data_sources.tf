locals {
  external_facts_dir    = "/etc/puppetlabs/facter/facts.d"
  bootstrap_script_path = "/usr/local/bin/ih-bootstrap"
}

data "aws_region" "current" {}

locals {
  puppet_manifest = var.puppet_manifest == null ? (
    "${var.puppet_root_directory}/environments/${var.environment}/manifests/site.pp"
  ) : var.puppet_manifest

  puppet_cmd = join(
    " ",
    concat(
      ["ih-puppet"],
      var.puppet_debug_logging ? ["--debug"] : [],
      [
        "--environment", var.environment,
        "--environmentpath", var.puppet_environmentpath,
        "--root-directory", var.puppet_root_directory,
        "--hiera-config", var.puppet_hiera_config_path,
        "--module-path", var.puppet_module_path,
      ],
      var.cancel_instance_refresh_on_error ? ["--cancel-instance-refresh-on-error"] : [],
      [
        "apply",
        local.puppet_manifest
      ]
    )
  )

  # Bootstrap script rendered into /usr/local/bin/ih-bootstrap and invoked
  # from runcmd as a single entry. Running through a script with set -euo
  # pipefail (instead of cloud-init's fail-open runcmd list) means any
  # failing step aborts bootstrap and /var/run/puppet-done is written only
  # on the success path. See issue #84.
  bootstrap_script = templatefile(
    "${path.module}/files/ih-bootstrap.sh.tpl",
    {
      lifecycle_hook_name = var.lifecycle_hook_name == null ? "" : var.lifecycle_hook_name
      mount_volumes       = length(var.mounts) > 0
      pre_runcmd          = var.pre_runcmd
      post_runcmd         = var.post_runcmd
      puppet_cmd          = local.puppet_cmd
    }
  )
}

data "cloudinit_config" "config" {
  gzip          = var.gzip_userdata
  base64_encode = true

  part {
    content_type = "text/cloud-config"
    content = join(
      "\n",
      [
        "#cloud-config",
        yamlencode(
          merge(
            #-------------------------------------------------------------------
            # SSH Host Keys Configuration
            # Configures pre-generated SSH host keys for consistent fingerprints
            #-------------------------------------------------------------------
            length(var.ssh_host_keys) > 0 ? { ssh_deletekeys : true } : {},
            length(var.ssh_host_keys) > 0 ?
            {
              ssh_keys : merge(
                {
                  for ssh_key in var.ssh_host_keys : format("%s_private", ssh_key.type) => ssh_key.private
                },
                {
                  for ssh_key in var.ssh_host_keys : format("%s_public", ssh_key.type) => ssh_key.public
                }
              )
            } : {},
            length(var.mounts) > 0 ? { mounts : var.mounts } : {},
            {
              bootcmd : [
                # Create auth inputs for APT repos
                "echo '${base64encode(local.repo_pairs_json)}' > /var/tmp/apt-auth.json.b64",
                "base64 -d /var/tmp/apt-auth.json.b64 > /var/tmp/apt-auth.json",
                # Prepare and run secret resolver
                "echo '${base64encode(file("${path.module}/files/apt_auth/generate_apt_auth.py"))}' > /var/tmp/generate_apt_auth.py.b64",
                "base64 -d /var/tmp/generate_apt_auth.py.b64 > /usr/local/bin/generate_apt_auth.py",

                # Probe for Python; log-and-skip if absent; otherwise run resolver
                "echo '${base64encode(file("${path.module}/files/generate_apt_auth.sh"))}' > /var/tmp/generate_apt_auth.sh.b64",
                "base64 -d /var/tmp/generate_apt_auth.sh.b64 > /usr/local/bin/generate_apt_auth.sh",
                "chmod +x /usr/local/bin/generate_apt_auth.sh",
                "AWS_DEFAULT_REGION=${data.aws_region.current.name} /usr/local/bin/generate_apt_auth.sh",

                # Prepare and run InfraHouse repo installer
                "echo '${base64encode(file("${path.module}/files/bootcmd.sh"))}' > /var/tmp/bootcmd.sh.b64",
                "base64 -d /var/tmp/bootcmd.sh.b64 > /usr/local/bin/bootcmd",
                "chmod +x /usr/local/bin/bootcmd",
                "/usr/local/bin/bootcmd"
              ]
              write_files : concat(
                [
                  {
                    content : local.bootstrap_script,
                    path : local.bootstrap_script_path,
                    permissions : "0755"
                  },
                  {
                    content : "export AWS_DEFAULT_REGION=${data.aws_region.current.name}",
                    path : "/etc/profile.d/aws.sh",
                    permissions : "0644"
                  },
                  {
                    content : join(
                      "\n",
                      [
                        "[default]",
                        "region=${data.aws_region.current.name}"
                      ]
                    ),
                    path : "/root/.aws/config",
                    permissions : "0600"
                  },
                  {
                    content : yamlencode(
                      {
                        puppet_role : var.role
                        puppet_environment : var.environment
                      }
                    ),
                    path : join(
                      "/", [
                        local.external_facts_dir,
                        "puppet.yaml"
                      ]
                    ),
                    permissions : "0644"
                  },
                  {
                    content : jsonencode(
                      {
                        ih-puppet : {
                          "debug" : var.puppet_debug_logging
                          "root-directory" : var.puppet_root_directory
                          "hiera-config" : var.puppet_hiera_config_path
                          "environmentpath" : var.puppet_environmentpath
                          "module-path" : var.puppet_module_path
                          "cancel_instance_refresh_on_error" : var.cancel_instance_refresh_on_error
                          "manifest" : local.puppet_manifest
                        }
                      }
                    ),
                    path : join(
                      "/", [
                        local.external_facts_dir,
                        "ih-puppet.json"
                      ]
                    ),
                    permissions : "0644"
                  },
                  {
                    content : jsonencode(var.custom_facts),
                    path : join(
                      "/", [
                        local.external_facts_dir,
                        "custom.json"
                      ]
                    ),
                    permissions : "0644"
                  }
                ],
                # oracular needs facter config to lookup puppet_role
                contains(["oracular"], var.ubuntu_codename) ? [
                  {
                    content : file("${path.module}/files/facter.conf"),
                    path : "/etc/facter/facter.conf",
                    permissions : "0644"
                  }
                ] : [],
                var.extra_files,
                local.repo_preferences,
              )
              package_update : true,
              apt : {
                sources : merge(
                  {
                    # The InfraHouse APT repository is now installed via bootcmd.sh script
                    # (see lines 54-58 above). The script fetches the GPG key from the
                    # repository URL, verifies its fingerprint, and creates the apt
                    # sources list at /etc/apt/sources.list.d/50-infrahouse.list.
                    # This approach avoids embedding the full GPG key in userdata.
                    #
                    # Previously it was installed here inline (retained for illustration):
                    # infrahouse : {
                    #   source : "deb [signed-by=$KEY_FILE] https://release-${var.ubuntu_codename}.infrahouse.com/ $RELEASE main"
                    #   key : file("${path.module}/files/DEB-GPG-KEY-infrahouse-${var.ubuntu_codename}")
                    # }
                  },
                  {
                    for repo in keys(var.extra_repos) : repo => merge(
                      {
                        source : var.extra_repos[repo].source
                      },
                      # Include 'key' if provided (embedded GPG key)
                      var.extra_repos[repo].key != null ? {
                        key : var.extra_repos[repo].key
                      } : {},
                      # Include 'keyid' if provided (fetch from keyserver)
                      var.extra_repos[repo].keyid != null ? {
                        keyid : var.extra_repos[repo].keyid
                      } : {},
                      # Include 'keyserver' if provided (custom keyserver for keyid)
                      var.extra_repos[repo].keyserver != null ? {
                        keyserver : var.extra_repos[repo].keyserver
                      } : {}
                    )
                  }
                )
              }
              packages : concat(
                [
                  # json gem dependencies
                  "make",
                  "gcc",
                  # puppet
                  "puppet-code",
                  "infrahouse-toolkit"
                ],
                contains(["noble", "oracular"], var.ubuntu_codename) ? ["ruby-rubygems", "ruby-dev"] : [],
                local.mount_packages,
                var.packages
              ),
              runcmd : [
                # Single entry so cloud-init's runcmd module cannot fail-open
                # between steps. The script runs under `set -euo pipefail`
                # and is the sole owner of the /var/run/puppet-done marker.
                "bash ${local.bootstrap_script_path}"
              ]
            }
          )
        )
      ]
    )
  }
}
