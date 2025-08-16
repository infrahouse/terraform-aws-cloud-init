resource "aws_launch_template" "cloud-init" {
  name_prefix   = "cloud-init-"
  instance_type = "t3a.micro"
  key_name      = aws_key_pair.cloud-init-test.key_name
  image_id      = local.ami_id
  iam_instance_profile {
    arn = module.instance-profile.instance_profile_arn
  }
  block_device_mappings {
    device_name = data.aws_ami.selected.root_device_name
    ebs {
      volume_size           = "8"
      delete_on_termination = true
      encrypted             = true
    }
  }
  metadata_options {
    http_tokens   = "required"
    http_endpoint = "enabled"
  }
  user_data = module.user-data.userdata
}
