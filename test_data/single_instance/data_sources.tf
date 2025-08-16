data "aws_ami" "ubuntu_pro" {
  most_recent = true

  filter {
    name   = "name"
    values = [local.ami_name_pattern_pro]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name = "state"
    values = [
      "available"
    ]
  }

  owners = ["099720109477"] # Canonical
}

data "aws_ami" "infrahouse_pro" {
  most_recent = true

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name = "state"
    values = [
      "available"
    ]
  }
  filter {
    name   = "tag:ubuntu_codename"
    values = [local.ubuntu_codename]
  }

  filter {
    name   = "tag:maintainer"
    values = ["infrahouse"]
  }
  owners = ["303467602807"] # InfraHouse
}

data "aws_iam_policy" "ssm" {
  name = "AmazonSSMManagedInstanceCore"
}

data "aws_ami" "selected" {
  filter {
    name = "image-id"
    values = [
      local.ami_id
    ]
  }
}
