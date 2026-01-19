# Troubleshooting

Common issues and solutions when using the terraform-aws-cloud-init module.

## Cloud-init Issues

### Cloud-init failed or stuck

**Symptoms:** Instance doesn't reach running state or cloud-init never completes.

**Diagnosis:**

```bash
# Check cloud-init status
cloud-init status

# View detailed logs
sudo cat /var/log/cloud-init-output.log
sudo cat /var/log/cloud-init.log
```

**Common causes:**

1. **Invalid userdata** - Check for YAML syntax errors
2. **Network issues** - Instance can't reach APT repositories
3. **IAM permissions** - Instance role missing required permissions

### Puppet completion marker not created

**Symptoms:** `/var/run/puppet-done` doesn't exist.

**Diagnosis:**

```bash
# Check if Puppet ran
sudo grep -i puppet /var/log/cloud-init-output.log

# Check for errors
sudo grep -i error /var/log/cloud-init-output.log
```

**Solution:** Check Puppet logs for errors. The marker is only created if all runcmd commands
succeed.

## Validation Errors

### Invalid environment name

**Error:**
```
Error: Invalid value for variable "environment"
environment must contain only lowercase letters, numbers, and underscores (no hyphens)
```

**Solution:** Use underscores instead of hyphens:

```hcl
# Wrong
environment = "my-environment"

# Correct
environment = "my_environment"
```

### Invalid role name

**Error:**
```
Error: Invalid value for variable "role"
role must contain only lowercase letters, numbers, and underscores (no hyphens)
```

**Solution:** Follow Puppet naming conventions:

```hcl
# Wrong
role = "web-server"

# Correct
role = "web_server"
```

### extra_repos validation error

**Error:**
```
Error: extra_repos: machine and authFrom must be both set or both unset
```

**Solution:** When using APT authentication, provide both `machine` and `authFrom`:

```hcl
extra_repos = {
  "myrepo" = {
    source   = "deb [signed-by=$KEY_FILE] https://apt.example.com noble main"
    keyid    = "ABC123..."
    machine  = "apt.example.com"   # Both required
    authFrom = "arn:aws:..."       # Both required
  }
}
```

## APT Repository Issues

### GPG key validation failed

**Symptoms:** Instance fails during bootcmd with GPG fingerprint mismatch.

**Diagnosis:**

```bash
sudo cat /var/log/cloud-init-output.log | grep -i gpg
```

**Solution:** This indicates the GPG key has been rotated or is incorrect. Update to the latest
module version which includes current key fingerprints.

### Private repository authentication failed

**Symptoms:** `apt update` fails with 401 Unauthorized.

**Diagnosis:**

```bash
# Check auth file was created
sudo cat /etc/apt/auth.conf.d/50user

# Check secret resolution log
sudo cat /var/log/cloud-init-output.log | grep -i secret
```

**Common causes:**

1. **Wrong secret ARN** - Verify the secret exists in the correct region
2. **IAM permissions** - Instance role needs `secretsmanager:GetSecretValue`
3. **Secret format** - Must be JSON: `{"apt": "username:password"}`

### Package installation failed

**Symptoms:** Packages from `var.packages` not installed.

**Diagnosis:**

```bash
sudo cat /var/log/cloud-init-output.log | grep -i "apt\|package"
dpkg -l | grep <package-name>
```

**Common causes:**

1. **Package not found** - Package doesn't exist in configured repositories
2. **Dependency issues** - Missing dependencies
3. **Repository not ready** - APT repository setup failed earlier

## Puppet Issues

### ih-puppet not found

**Error:** `ih-puppet: command not found`

**Diagnosis:**

```bash
which ih-puppet
pip show infrahouse-toolkit
```

**Solution:** Check that `infrahouse-toolkit` installed successfully. Verify the InfraHouse APT
repository is correctly configured.

### Puppet manifest not found

**Error:** `Error: Could not find manifest /opt/puppet-code/environments/.../site.pp`

**Solution:** Ensure `puppet-code` package is installed and contains the expected manifest at
the configured path. Check `puppet_root_directory` and `puppet_manifest` variables.

### Puppet facts not available

**Symptoms:** Puppet can't find `puppet_role` or `puppet_environment` facts.

**Diagnosis:**

```bash
sudo cat /etc/puppetlabs/facter/facts.d/puppet.yaml
facter puppet_role
facter puppet_environment
```

**Solution:** Ensure cloud-init completed the write_files phase successfully.

## Userdata Issues

### Userdata too large

**Error:** `InvalidParameterValue: User data is limited to 16384 bytes`

**Solutions:**

1. **Enable gzip compression:**
   ```hcl
   gzip_userdata = true
   ```

2. **Use `keyid` instead of `key`** for APT repositories

3. **Reduce `extra_files`** content size

4. **Move large files** to S3 and download in `pre_runcmd`

### Userdata changes not applied

**Symptoms:** Updated module configuration not reflected on new instances.

**Solution:** Ensure launch template version is updated:

```hcl
resource "aws_instance" "example" {
  launch_template {
    id      = aws_launch_template.example.id
    version = "$Latest"  # Or specific version
  }
}
```

## AWS Issues

### IAM permissions insufficient

**Error:** Various AWS API errors during cloud-init.

**Required permissions for instance role:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:apt-*"
      ]
    }
  ]
}
```

### Wrong region configured

**Symptoms:** AWS CLI commands fail or access wrong region.

**Diagnosis:**

```bash
cat /root/.aws/config
aws configure list
```

**Solution:** The module automatically configures the region from the instance metadata. Ensure
the AWS provider is configured for the correct region.

## Getting Help

If you're still stuck:

1. **Check cloud-init logs** thoroughly:
   ```bash
   sudo cat /var/log/cloud-init-output.log
   sudo journalctl -u cloud-init
   ```

2. **Enable debug logging:**
   ```hcl
   puppet_debug_logging = true
   ```

3. **Open an issue** on [GitHub](https://github.com/infrahouse/terraform-aws-cloud-init/issues)
   with:
   - Terraform configuration (sanitized)
   - Error messages
   - Relevant log output