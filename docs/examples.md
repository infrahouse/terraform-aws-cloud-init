# Examples

Common use cases and configurations for the terraform-aws-cloud-init module.

## Basic Web Server

Minimal configuration for a web server:

```hcl
module "webserver_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment = "production"
  role        = "webserver"
}
```

## With Custom Packages

Install additional packages during bootstrap:

```hcl
module "webserver_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment = "production"
  role        = "webserver"

  packages = [
    "nginx",
    "certbot",
    "python3-certbot-nginx"
  ]
}
```

## With Custom Facts

Inject custom Puppet facts:

```hcl
module "app_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment = "production"
  role        = "app_server"

  custom_facts = {
    app_version     = var.app_version
    cluster_name    = "web-cluster-1"
    feature_flags   = jsonencode(var.feature_flags)
  }
}
```

## With Pre/Post Commands

Run commands before and after Puppet:

```hcl
module "app_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment = "production"
  role        = "app_server"

  pre_runcmd = [
    "mkdir -p /opt/myapp/data",
    "chown -R ubuntu:ubuntu /opt/myapp"
  ]

  post_runcmd = [
    "systemctl enable myapp",
    "systemctl start myapp"
  ]
}
```

## With EBS Volume Mounts

Mount EBS volumes before Puppet runs:

```hcl
module "database_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment = "production"
  role        = "database"

  mounts = [
    ["/dev/xvdf", "/var/lib/postgresql", "ext4", "defaults,nofail", "0", "2"]
  ]

  pre_runcmd = [
    "mkfs -t ext4 /dev/xvdf || true"  # Format if not already formatted
  ]
}
```

## With Private APT Repository

Configure a private APT repository with authentication:

```hcl
module "app_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment = "production"
  role        = "app_server"

  extra_repos = {
    "company-repo" = {
      source   = "deb [signed-by=$KEY_FILE] https://apt.company.com/ubuntu noble main"
      keyid    = "A627B7760019BA51B903453D37A181B689AD619"
      machine  = "apt.company.com"
      authFrom = "arn:aws:secretsmanager:us-west-2:123456789012:secret:apt-credentials"
      priority = 500
    }
  }
}
```

The secret in AWS Secrets Manager must contain JSON with the username as key and password as value:

```json
{
  "deploy": "s3cr3t-p4ssw0rd"
}
```

This generates an APT auth entry: `machine apt.company.com login deploy password s3cr3t-p4ssw0rd`

See [Architecture - Secret Format](architecture.md#secret-format) for details.

## With SSH Host Keys

Pre-configure SSH host keys for consistent identification:

```hcl
module "jumphost_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment = "production"
  role        = "jumphost"

  ssh_host_keys = [
    {
      type    = "rsa"
      private = data.aws_secretsmanager_secret_version.ssh_rsa.secret_string
      public  = data.aws_secretsmanager_secret_version.ssh_rsa_pub.secret_string
    },
    {
      type    = "ed25519"
      private = data.aws_secretsmanager_secret_version.ssh_ed25519.secret_string
      public  = data.aws_secretsmanager_secret_version.ssh_ed25519_pub.secret_string
    }
  ]
}
```

!!! warning "Security Consideration"
    Embedding SSH host keys in userdata exposes them to anyone with EC2 read access
    (`ec2:DescribeInstanceAttribute`) or instance metadata access. While host keys only
    prove server identity (not grant access), an attacker with the key AND a network
    MITM position could impersonate the server.

    For higher security environments, consider fetching host keys from Secrets Manager
    in `pre_runcmd` instead:

    ```hcl
    pre_runcmd = [
      "aws secretsmanager get-secret-value --secret-id ssh-host-key-ed25519 --query SecretString --output text > /etc/ssh/ssh_host_ed25519_key",
      "chmod 600 /etc/ssh/ssh_host_ed25519_key",
    ]
    ```

    This requires AWS CLI to be installed (available after package installation phase).

## With Extra Configuration Files

Create additional configuration files:

```hcl
module "app_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment = "production"
  role        = "app_server"

  extra_files = [
    {
      content     = file("${path.module}/files/app-config.yaml")
      path        = "/etc/myapp/config.yaml"
      permissions = "0644"
    },
    {
      content     = templatefile("${path.module}/files/env.tpl", {
        database_host = var.database_host
        redis_host    = var.redis_host
      })
      path        = "/etc/myapp/.env"
      permissions = "0600"
    }
  ]
}
```

## With Gzip Compression

Enable compression for large userdata:

```hcl
module "app_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment    = "production"
  role           = "app_server"
  gzip_userdata  = true

  # Large configuration that might exceed 16KB limit
  extra_repos = { /* multiple repos */ }
  extra_files = [ /* multiple files */ ]
}
```

## With Debug Logging

Enable verbose Puppet output for troubleshooting:

```hcl
module "app_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment         = "development"
  role                = "app_server"
  puppet_debug_logging = true
}
```

## Complete Production Example

A comprehensive example combining multiple features:

```hcl
module "production_app_userdata" {
  source  = "registry.infrahouse.com/infrahouse/cloud-init/aws"
  version = "2.2.3"

  environment = "production"
  role        = "app_server"

  # Additional packages
  packages = ["jq", "awscli"]

  # Custom facts
  custom_facts = {
    app_version  = var.app_version
    deploy_id    = var.deploy_id
    cluster_name = var.cluster_name
  }

  # Private repository
  extra_repos = {
    "company-repo" = {
      source   = "deb [signed-by=$KEY_FILE] https://apt.company.com/ubuntu noble main"
      keyid    = var.company_repo_keyid
      machine  = "apt.company.com"
      authFrom = var.apt_secret_arn
    }
  }

  # Configuration files
  extra_files = [
    {
      content     = templatefile("${path.module}/templates/app.conf.tpl", local.app_config)
      path        = "/etc/myapp/app.conf"
      permissions = "0644"
    }
  ]

  # Mount data volume
  mounts = [
    ["/dev/xvdf", "/data", "ext4", "defaults,nofail", "0", "2"]
  ]

  # Pre-puppet commands
  pre_runcmd = [
    "mkfs -t ext4 /dev/xvdf || true"
  ]

  # Post-puppet commands
  post_runcmd = [
    "systemctl daemon-reload",
    "systemctl restart myapp"
  ]

  # Compress large userdata
  gzip_userdata = true
}
```