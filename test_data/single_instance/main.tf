resource "aws_instance" "cloud-init" {

  subnet_id = var.subnet_id
  launch_template {
    id      = aws_launch_template.cloud-init.id
    version = aws_launch_template.cloud-init.latest_version
  }

  user_data_base64            = module.user-data.userdata
  user_data_replace_on_change = true

}
