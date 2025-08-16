locals {
  external_facts_dir = "/etc/puppetlabs/facter/facts.d"
}

data "aws_region" "current" {}

locals {
  pre_puppet_cmd  = length(var.mounts) > 0 ? ["mount -a"] : []
  puppet_manifest = var.puppet_manifest == null ? "${var.puppet_root_directory}/environments/${var.environment}/manifests/site.pp" : var.puppet_manifest
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
                "echo '${file("${path.module}/files/bootcmd.sh")}' > /tmp/bootcmd.sh",
                "bash /tmp/bootcmd.sh"
              ]
              write_files : concat(
                [
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
                var.extra_files
              )
              package_update : true,
              apt : {
                sources : merge(
                  {
                    # This is retained here for the purpose of illustration.
                    # infrahouse : {
                    #   source : "deb [signed-by=$KEY_FILE] https://release-${var.ubuntu_codename}.infrahouse.com/ $RELEASE main"
                    #   key : file("${path.module}/files/DEB-GPG-KEY-infrahouse-${var.ubuntu_codename}")
                    # }
                  },
                  var.extra_repos
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
                var.packages
              ),
              runcmd : concat(
                local.pre_puppet_cmd,
                [
                  "PATH=/opt/puppetlabs/puppet/bin:$PATH gem install json",
                  "PATH=/opt/puppetlabs/puppet/bin:$PATH gem install aws-sdk-core",
                  "PATH=/opt/puppetlabs/puppet/bin:$PATH gem install aws-sdk-secretsmanager",
                ],
                var.pre_runcmd,
                [
                  join(
                    " ",
                    concat(
                      [
                        "ih-puppet",
                        var.puppet_debug_logging ? "--debug" : "",
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
                ],
                var.post_runcmd,
              )
            }
          )
        )
      ]
    )
  }
}
