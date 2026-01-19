# Architecture

This page explains how the terraform-aws-cloud-init module works internally.

## Overview

The module generates a cloud-init configuration that bootstraps EC2 instances for Puppet-managed
infrastructure. The output is a base64-encoded, multi-part MIME message that cloud-init processes
during instance first boot.

## Execution Flow

![Cloud-Init Bootstrap Flow](assets/architecture.png)

## Cloud-init Phases

### 1. bootcmd Phase

Runs early in boot, before package installation. This phase:

- **Sets up APT authentication** - If `authFrom` is configured, runs a Python script
  (`generate_apt_auth.py`) that fetches credentials from AWS Secrets Manager using `boto3`.

    !!! warning "InfraHouse AMI Required for authFrom"
        The `authFrom` feature requires `boto3` (AWS SDK for Python), which is **not installed
        on vanilla Ubuntu**. You must use the InfraHouse AMI or pre-install boto3 on your
        custom AMI for this feature to work.

- **Installs InfraHouse APT repository** - Downloads and validates GPG keys, creates the apt
  sources list at `/etc/apt/sources.list.d/50-infrahouse.list`. This works on vanilla Ubuntu
  as it only requires `curl` and `gpg`.

### 2. write_files Phase

Creates configuration files needed by Puppet and AWS tooling:

| File | Purpose |
|------|---------|
| `/root/.aws/config` | AWS CLI region configuration |
| `/etc/puppetlabs/facter/facts.d/puppet.yaml` | Puppet role and environment facts |
| `/etc/puppetlabs/facter/facts.d/ih-puppet.json` | ih-puppet configuration |
| `/etc/puppetlabs/facter/facts.d/custom.json` | Custom facts from `var.custom_facts` |

### 3. Package Installation

Installs required packages:

- `puppet-code` - Puppet manifests and code
- `infrahouse-toolkit` - InfraHouse tools including `ih-puppet`
- `ruby-rubygems`, `ruby-dev` - Ruby dependencies (on noble/oracular)
- Custom packages from `var.packages`

### 4. runcmd Phase

Executes commands in order:

1. **Mount volumes** - Runs `mount -a` if `var.mounts` is configured
2. **Install Ruby gems** - Installs `json`, `aws-sdk-core`, `aws-sdk-secretsmanager`
3. **Pre-runcmd** - User commands from `var.pre_runcmd`
4. **ih-puppet apply** - Runs Puppet with configured options
5. **Post-runcmd** - User commands from `var.post_runcmd`
6. **Completion marker** - Creates `/var/run/puppet-done`

## Puppet Facts

The module injects several facts for Puppet to use:

```yaml
# /etc/puppetlabs/facter/facts.d/puppet.yaml
puppet_role: webserver
puppet_environment: production
```

```json
// /etc/puppetlabs/facter/facts.d/ih-puppet.json
{
  "ih-puppet": {
    "debug": false,
    "root-directory": "/opt/puppet-code",
    "hiera-config": "{root_directory}/environments/{environment}/hiera.yaml",
    "environmentpath": "{root_directory}/environments",
    "module-path": "{root_directory}/modules",
    "manifest": "/opt/puppet-code/environments/production/manifests/site.pp"
  }
}
```

## APT Repository Authentication

For private APT repositories requiring authentication, the module:

1. Embeds a Python script (`generate_apt_auth.py`) in bootcmd
2. Reads repository configuration from `/var/tmp/apt-auth.json`
3. Fetches credentials from AWS Secrets Manager using `boto3` and the instance's IAM role
4. Writes credentials to `/etc/apt/auth.conf.d/50user` with 0600 permissions

!!! warning "Requires InfraHouse AMI"
    This feature requires `boto3` which is not available on vanilla Ubuntu AMIs.
    Use the InfraHouse AMI or pre-install boto3 on your custom AMI.

### Secret Format

The AWS Secrets Manager secret must contain JSON with a single key-value pair:

```json
{
  "<username>": "<password>"
}
```

**Example:** For a repository with username `deploy` and password `s3cr3t`:

```json
{
  "deploy": "s3cr3t"
}
```

This generates the following entry in `/etc/apt/auth.conf.d/50user`:

```
machine apt.example.com login deploy password s3cr3t
```

!!! note "Only the first key-value pair is used"
    If your secret contains multiple key-value pairs, only the first one will be used
    for authentication.

## GPG Key Validation

The InfraHouse APT repository installation validates GPG key fingerprints:

```bash
# bootcmd.sh validates the key fingerprint before trusting it
EXPECTED_FINGERPRINT="..."
ACTUAL_FINGERPRINT=$(gpg --show-keys --with-fingerprint key.gpg | grep -o '[A-F0-9 ]\{50\}')
if [ "$ACTUAL_FINGERPRINT" != "$EXPECTED_FINGERPRINT" ]; then
    exit 1
fi
```

## Using the InfraHouse AMI

The InfraHouse AMI is a pre-built Ubuntu Pro image that includes `boto3` and other dependencies
required for features like `authFrom`. The AMI is built from
[infrahouse/infrahouse-ubuntu-pro](https://github.com/infrahouse/infrahouse-ubuntu-pro).

### Available Regions

Currently, the InfraHouse AMI is only available in **us-west-1**.

### Finding the AMI

```hcl
data "aws_ami" "infrahouse" {
  most_recent = true
  owners      = ["303467602807"]  # InfraHouse

  filter {
    name   = "name"
    values = ["infrahouse-ubuntu-pro-noble-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
```

### Using in Other Regions

If you need the InfraHouse AMI in a region other than us-west-1, you have two options:

**Option 1: Copy the AMI**

```bash
# Find the latest InfraHouse AMI in us-west-1
AMI_ID=$(aws ec2 describe-images \
  --region us-west-1 \
  --owners 303467602807 \
  --filters "Name=name,Values=infrahouse-ubuntu-pro-noble-*" \
  --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
  --output text)

# Copy to your target region
aws ec2 copy-image \
  --source-region us-west-1 \
  --source-image-id $AMI_ID \
  --region us-east-1 \
  --name "infrahouse-ubuntu-pro-noble-copy"
```

**Option 2: Build your own AMI**

Install `boto3` on a vanilla Ubuntu image:

```bash
apt-get update && apt-get install -y python3-boto3
```

Or use `pre_runcmd` to install it (note: this won't help with `authFrom` since bootcmd runs first):

```hcl
# This does NOT work for authFrom - boto3 must be pre-installed
pre_runcmd = ["apt-get update && apt-get install -y python3-boto3"]
```

## Userdata Size Considerations

AWS limits userdata to 16KB (compressed). The module provides options to manage size:

- **Use `keyid` instead of `key`** - GPG keys are ~3-5KB each; key IDs are ~50 bytes
- **Enable `gzip_userdata`** - Compresses the cloud-init configuration
- **Minimize `extra_files`** - Large embedded files consume userdata space