# Getting Started

This guide walks you through deploying your first EC2 instance using the terraform-aws-cloud-init
module.

## Prerequisites

Before using this module, ensure you have:

1. **Terraform** >= 1.5 installed
2. **AWS credentials** configured (via environment variables, shared credentials file, or IAM role)
3. **Puppet code repository** - The `puppet-code` package installed from InfraHouse APT repository
4. **IAM instance profile** - Your EC2 instances need an instance profile for AWS API access

## Basic Deployment

### Step 1: Create the userdata module

```hcl
module "webserver_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment = var.environment
  role        = "webserver"
}
```

### Step 2: Create a launch template

```hcl
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-noble-24.04-amd64-server-*"]
  }
}

resource "aws_launch_template" "webserver" {
  name_prefix   = "webserver-"
  instance_type = "t3.micro"
  image_id      = data.aws_ami.ubuntu.id

  iam_instance_profile {
    arn = aws_iam_instance_profile.webserver.arn
  }

  user_data = module.webserver_userdata.userdata

  tags = {
    Name        = "webserver"
    environment = var.environment
  }
}
```

### Step 3: Launch an instance

```hcl
resource "aws_instance" "webserver" {
  launch_template {
    id      = aws_launch_template.webserver.id
    version = "$Latest"
  }

  subnet_id = var.subnet_id

  tags = {
    Name = "webserver"
  }
}
```

## Verifying the Deployment

After the instance launches, cloud-init will:

1. Configure AWS CLI with the region
2. Set up Puppet facts for environment and role
3. Install the InfraHouse APT repository
4. Install `puppet-code` and `infrahouse-toolkit`
5. Run `ih-puppet` to apply your Puppet manifests
6. Create `/var/run/puppet-done` marker file

You can check cloud-init progress:

```bash
# SSH into the instance
ssh ubuntu@<instance-ip>

# Check cloud-init status
cloud-init status --wait

# View cloud-init logs
sudo cat /var/log/cloud-init-output.log

# Verify Puppet ran successfully
ls -la /var/run/puppet-done
```

## Next Steps

- [Configuration](configuration.md) - Learn about all available variables
- [Examples](examples.md) - See common use cases
- [Architecture](architecture.md) - Understand how the module works