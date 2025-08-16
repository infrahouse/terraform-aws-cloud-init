locals {
  ubuntu_codename      = "noble"
  ami_name_pattern_pro = "ubuntu-pro-server/images/hvm-ssd-gp3/ubuntu-${local.ubuntu_codename}-*"
  ami_id               = var.ami_vendor == "infrahouse" ? data.aws_ami.infrahouse_pro.id : data.aws_ami.ubuntu_pro.id
}
