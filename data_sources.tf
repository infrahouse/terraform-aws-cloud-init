locals {
  external_facts_dir = "/etc/puppetlabs/facter/facts.d"
}

data "aws_region" "current" {}

data "cloudinit_config" "config" {
  gzip          = false
  base64_encode = true

  part {
    content_type = "text/cloud-config"
    content = join(
      "\n",
      [
        "#cloud-config",
        yamlencode(
          {
            write_files : concat(
              [
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
                        "module-path" : var.puppet_module_path
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
                }
              ],
              var.extra_files
            )
            "package_update" : true,
            apt : {
              sources : merge(
                {
                  infrahouse : {
                    source : "deb [signed-by=$KEY_FILE] https://release-${var.ubuntu_codename}.infrahouse.com/ $RELEASE main"
                    key : file("${path.module}/files/DEB-GPG-KEY-infrahouse-${var.ubuntu_codename}")
                  }
                },
                var.extra_repos
              )
            }
            packages : concat(
              [
                "puppet-code",
                "infrahouse-toolkit"
              ],
              var.packages
            ),
            puppet : {
              install : true,
              install_type : "aio",
              collection : "puppet8",
              package_name : "puppet-agent",
              start_service : false,
            }
            runcmd : [
              concat(
                [
                  "ih-puppet",
                ],
                var.puppet_debug_logging ? ["--debug"] : [],
                [
                  "--environment", var.environment,
                  "--root-directory", var.puppet_root_directory,
                  "--hiera-config", var.puppet_hiera_config_path,
                  "--module-path", var.puppet_module_path,
                  "apply"
                ]
              )
            ]
          }
        )
      ]
    )
  }
}
