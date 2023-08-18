# terraform-aws-cloud-init
This is a module to prepare a userdata for an EC2 instance.
The instance will be provisioned by [Puppet](https://www.puppet.com/).

Before Puppet kicks in, [Cloud-init](https://cloudinit.readthedocs.io/en/latest/index.html) pre-configures the instance.

* AWS config file `/root/.aws/config`

It is expected the instance will have an instance profile, so no AWS credentials need to be provisioned separately. 
However, the AWS tools need a default region.

* Puppet facts in `/etc/puppetlabs/facter/facts.d`

Puppet needs to know what role the instance has, and in what environment the instance runs. 
These parameters are passed as puppet facts.

* InfraHouse package repository

Tools as well as the puppet code will be installed from the infrahouse APT repository.

* Bootstrap packages

  * `puppet-code` - the puppet manifests and other code.
  * `infrahouse-toolkit` - The InfraHouse toolkit. Specifically, we need a puppet wrapper `ih-ppuppet`.

Finally, [Cloud-init](https://cloudinit.readthedocs.io/en/latest/index.html) runs a puppet wrapper (`ih-puppet`) to apply
manifests from the `puppet-code`.

## Usage

The module prepares userdata:
```hcl
module "jumphost_userdata" {
  source  = "infrahouse/cloud-init/aws"
  version = "~> 1.0"
  environment    = var.environment
  gpg_public_key = file("./files/DEB-GPG-KEY-infrahouse-jammy")
  role           = "jumphost"
}
```
that we can later on use in a launch template or an instance config.
```hcl
resource "aws_launch_template" "jumphost" {
  name_prefix   = "jumphost-"
  instance_type = "t3a.micro"
  key_name      = var.keypair_name
  image_id      = var.ami_id == null ? data.aws_ami.ubuntu.id : var.ami_id
  iam_instance_profile {
    arn = module.jumphost_profile.instance_profile_arn
  }
  user_data = module.jumphost_userdata.userdata
}
```

## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 5.11 |
| <a name="requirement_template"></a> [template](#requirement\_template) | ~> 2.2 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 5.11 |
| <a name="provider_template"></a> [template](#provider\_template) | ~> 2.2 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |
| [template_cloudinit_config.config](https://registry.terraform.io/providers/hashicorp/template/latest/docs/data-sources/cloudinit_config) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_environment"></a> [environment](#input\_environment) | Environment name. Passed on as a puppet fact | `string` | n/a | yes |
| <a name="input_gpg_public_key"></a> [gpg\_public\_key](#input\_gpg\_public\_key) | Public GPG key used to verify signature of the InfraHouse releases repo. | `string` | n/a | yes |
| <a name="input_role"></a> [role](#input\_role) | Puppet role. Passed on as a puppet fact | `string` | n/a | yes |
| <a name="input_ubuntu_codename"></a> [ubuntu\_codename](#input\_ubuntu\_codename) | Ubuntu version to use for the jumphost | `string` | `"jammy"` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_userdata"></a> [userdata](#output\_userdata) | Rendered user-data with cloudinit config. |
