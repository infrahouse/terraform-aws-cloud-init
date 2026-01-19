# Configuration

This page documents all variables available in the terraform-aws-cloud-init module.

## Required Variables

### `environment`

Environment name passed as a Puppet fact.

- **Type:** `string`
- **Required:** Yes

```hcl
environment = "production"
```

!!! warning "Naming Convention"
    Must contain only lowercase letters, numbers, and underscores. Hyphens are not allowed.
    This follows Puppet naming conventions.

### `role`

Puppet role passed as a fact.

- **Type:** `string`
- **Required:** Yes

```hcl
role = "webserver"
```

!!! warning "Naming Convention"
    Must contain only lowercase letters, numbers, and underscores. Hyphens are not allowed.

## Optional Variables

### `ubuntu_codename`

Ubuntu version codename. Determines which InfraHouse repository to configure.

- **Type:** `string`
- **Default:** `"noble"`

```hcl
ubuntu_codename = "noble"
```

!!! note "Supported Versions"
    Only Ubuntu LTS versions are supported. Currently: `noble` (24.04 LTS).

### `packages`

Additional packages to install during bootstrap.

- **Type:** `list(string)`
- **Default:** `[]`

```hcl
packages = ["nginx", "htop", "jq"]
```

!!! info
    `puppet-code` and `infrahouse-toolkit` are always installed automatically.

### `custom_facts`

Custom Puppet facts to inject into the instance.

- **Type:** `any`
- **Default:** `{}`

```hcl
custom_facts = {
  app_version  = "1.2.3"
  cluster_name = "web-cluster"
}
```

Facts are written to `/etc/puppetlabs/facter/facts.d/custom.json`.

### `extra_files`

Additional files to create on the instance.

- **Type:** `list(object)`
- **Default:** `[]`

```hcl
extra_files = [
  {
    content     = "my config content"
    path        = "/etc/myapp/config.txt"
    permissions = "0644"
  }
]
```

### `extra_repos`

Additional APT repositories to configure.

- **Type:** `map(object)`
- **Default:** `{}`

=== "With GPG Key"

    ```hcl
    extra_repos = {
      "myrepo" = {
        source = "deb [signed-by=$KEY_FILE] https://apt.example.com/ubuntu noble main"
        key    = file("path/to/gpg-key.asc")
      }
    }
    ```

=== "With Key ID (Recommended)"

    ```hcl
    extra_repos = {
      "myrepo" = {
        source    = "deb [signed-by=$KEY_FILE] https://apt.example.com/ubuntu noble main"
        keyid     = "A627B7760019BA51B903453D37A181B689AD619"
        keyserver = "keyserver.ubuntu.com"  # optional
      }
    }
    ```

=== "With Authentication"

    ```hcl
    extra_repos = {
      "private-repo" = {
        source   = "deb [signed-by=$KEY_FILE] https://apt.example.com/ubuntu noble main"
        keyid    = "A627B7760019BA51B903453D37A181B689AD619"
        machine  = "apt.example.com"
        authFrom = "arn:aws:secretsmanager:us-west-2:123456789012:secret:apt-creds"
      }
    }
    ```

!!! tip "Save Userdata Space"
    Use `keyid` instead of `key` to reduce userdata size by ~3KB per repository.

### `pre_runcmd`

Commands to run before Puppet applies the manifest.

- **Type:** `list(string)`
- **Default:** `[]`

```hcl
pre_runcmd = [
  "mkdir -p /opt/myapp",
  "echo 'Starting bootstrap' >> /var/log/bootstrap.log"
]
```

### `post_runcmd`

Commands to run after Puppet applies the manifest.

- **Type:** `list(string)`
- **Default:** `[]`

```hcl
post_runcmd = [
  "systemctl restart nginx",
  "echo 'Bootstrap complete' >> /var/log/bootstrap.log"
]
```

### `ssh_host_keys`

Pre-configured SSH host keys for consistent host identification.

- **Type:** `list(object)`
- **Default:** `[]`
- **Sensitive:** Yes

```hcl
ssh_host_keys = [
  {
    type    = "rsa"
    private = file("keys/ssh_host_rsa_key")
    public  = file("keys/ssh_host_rsa_key.pub")
  }
]
```

### `mounts`

Volumes to mount before Puppet runs.

- **Type:** `list(list(string))`
- **Default:** `[]`

```hcl
mounts = [
  ["/dev/xvdf", "/data", "ext4", "defaults,nofail", "0", "2"]
]
```

### `gzip_userdata`

Whether to gzip compress the userdata.

- **Type:** `bool`
- **Default:** `false`

```hcl
gzip_userdata = true
```

!!! tip
    Enable this if your userdata exceeds AWS limits (16KB compressed).

### Puppet Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `puppet_root_directory` | Path where puppet code is hosted | `/opt/puppet-code` |
| `puppet_environmentpath` | Path for directory environments | `{root_directory}/environments` |
| `puppet_hiera_config_path` | Path to hiera configuration | `{root_directory}/environments/{environment}/hiera.yaml` |
| `puppet_module_path` | Path to common puppet modules | `{root_directory}/modules` |
| `puppet_manifest` | Path to puppet manifest | `null` (uses default) |
| `puppet_debug_logging` | Enable debug logging | `false` |
| `cancel_instance_refresh_on_error` | Cancel ASG refresh on error | `false` |

## Outputs

### `userdata`

Base64-encoded cloud-init configuration ready to use in launch templates.

```hcl
output "userdata" {
  description = "Rendered user-data with cloudinit config"
  value       = module.cloud_init.userdata
}
```