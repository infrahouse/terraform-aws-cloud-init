locals {
  external_facts_dir = "/etc/puppetlabs/facter/facts.d"
}

data "aws_region" "current" {}

data "template_cloudinit_config" "config" {
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
            write_files : [
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
              }
            ]
            "package_update" : true,
            apt : {
              sources : {
                infrahouse : {
                  source : "deb [signed-by=$KEY_FILE] https://release-${var.ubuntu_codename}.infrahouse.com/ $RELEASE main"
                  key : var.gpg_public_key
                }
              }
            }
            packages : [
              "puppet-code",
              "infrahouse-toolkit"
            ],
            puppet : {
              install : true,
              install_type : "aio",
              collection : "puppet8",
              package_name : "puppet-agent",
              start_service : false,
            }
            runcmd : [
              [
                "ih-puppet", "--debug", "apply"
              ]
            ]
          }
        )
      ]
    )
  }
}
