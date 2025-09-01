data "aws_iam_policy_document" "required_permissions" {
  statement {
    actions   = ["sts:GetCallerIdentity"]
    resources = ["*"]
  }
}

module "instance-profile" {
  source       = "registry.infrahouse.com/infrahouse/instance-profile/aws"
  version      = "1.9.0"
  permissions  = data.aws_iam_policy_document.required_permissions.json
  profile_name = "cloudinit_test"
}
