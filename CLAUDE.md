# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Terraform module that generates cloud-init userdata for EC2 instances in a Puppet-managed infrastructure. The module bridges the gap between AWS instance launch and Puppet configuration by handling bootstrapping tasks including AWS tooling setup, Puppet facts injection, APT repository configuration, and Puppet execution.

**Key output**: A base64-encoded cloud-init configuration (userdata) that can be used in AWS launch templates or instance configurations.

## Common Development Commands

### Testing
```bash
# Run all tests
make test

# Run tests and keep infrastructure (useful during development)
make test-keep

# Run tests and clean up (before creating PRs)
make test-clean
```

### Code Quality
```bash
# Format all code (Terraform + Python)
make format

# Check code style without modifying files
make lint

# Install git hooks (automatically done by bootstrap)
make install-hooks
```

### Bootstrap Environment
```bash
# Set up development environment (run in virtualenv)
make bootstrap
```

## Architecture

### Cloud-init Generation Flow

The module constructs a multi-part cloud-init configuration in `data_sources.tf`:

1. **bootcmd phase**: Runs before package installation
   - Resolves APT repository authentication using AWS Secrets Manager
   - Installs InfraHouse APT repository GPG keys and sources
   - Scripts: `files/generate_apt_auth.sh`, `files/apt_auth/generate_apt_auth.py`, `files/bootcmd.sh`

2. **write_files phase**: Creates configuration files
   - AWS config: `/root/.aws/config` with region
   - Puppet facts: `/etc/puppetlabs/facter/facts.d/puppet.yaml` (role, environment)
   - ih-puppet config: `/etc/puppetlabs/facter/facts.d/ih-puppet.json` (paths, debug settings)
   - Custom facts: `/etc/puppetlabs/facter/facts.d/custom.json` (from `var.custom_facts`)
   - Extra files from `var.extra_files` and generated APT preferences

3. **packages phase**: Installs packages
   - Core packages: `puppet-code`, `infrahouse-toolkit`
   - Additional packages from `var.packages`
   - Ubuntu-specific dependencies (ruby-rubygems for noble/oracular)

4. **runcmd phase**: Executes commands
   - Mounts volumes if configured (`mount -a`)
   - Installs Ruby gems: json, aws-sdk-core, aws-sdk-secretsmanager
   - Runs `var.pre_runcmd` commands
   - Executes `ih-puppet` to apply Puppet manifests
   - Runs `var.post_runcmd` commands

### Extra Repositories Feature

The `var.extra_repos` variable allows configuring additional APT repositories beyond the default InfraHouse repo:

- **Authentication**: Supports AWS Secrets Manager-based credentials via `machine`/`authFrom` fields
- **Priority**: APT preferences files generated when `priority` is specified (in `locals.tf`)
- **Secrets resolution**: `files/apt_auth/generate_apt_auth.py` fetches credentials from Secrets Manager

### Key Variables

- `environment` (required): Puppet environment name, passed as fact
- `role` (required): Puppet role, passed as fact
- `ubuntu_codename`: Ubuntu version for repository selection (default: "jammy")
- `puppet_root_directory`: Where puppet-code is installed (default: "/opt/puppet-code")
- `extra_repos`: Map of additional APT repositories with auth and priority support
- `custom_facts`: Additional Puppet facts to inject
- `ssh_host_keys`: Pre-configured SSH host keys for instances

## Testing

### Test Structure

Tests use `pytest-infrahouse` fixtures that create real AWS infrastructure:

- `tests/conftest.py`: Shared configuration (TERRAFORM_ROOT_DIR = "test_data")
- `tests/test_module.py`: Basic module functionality tests
- `tests/test_single_instance.py`: End-to-end EC2 instance tests
- `tests/test_apt_source.py`: APT repository configuration tests

### Test Data Directories

- `test_data/test_module/`: Minimal module usage
- `test_data/single_instance/`: Complete EC2 instance with launch template
- `test_data/apt_source/`: APT source configuration testing

### AWS Provider Version Testing

**CRITICAL**: Tests must run against both AWS provider versions 5 and 6. This is enforced via `@pytest.mark.parametrize("aws_provider_version", ["~> 5.11", "~> 6.0"])`. Tests dynamically rewrite `terraform.tf` to switch provider versions.

## Coding Standards

**ALWAYS read `.claude/CODING_STANDARD.md` before writing or modifying code.** Key points:

### Terraform-Specific Rules

1. **Validation blocks with nullable variables**: Use ternary operators, NOT logical OR
   ```hcl
   # CORRECT
   condition = var.value == null ? true : var.value <= 100

   # WRONG - fails if var.value is null
   condition = var.value == null || var.value <= 100
   ```

2. **Module pinning**: Always use exact versions (no ranges) for InfraHouse modules from `registry.infrahouse.com`

3. **IAM policies**: Always use `data "aws_iam_policy_document"`, never hand-crafted JSON

4. **Tagging**: Use lowercase tags except `Name`. Include `created_by_module` provenance tag.

### Python Rules

1. **Type hints required** for all functions
2. **Use pytest** with both happy and unhappy path tests
3. **Never use bare `except Exception:`** - catch specific exceptions or let it crash
4. **Use `setup_logging()` from infrahouse-core**
5. **Pin dependencies** with `~=` syntax (e.g., `requests ~= 2.31`)

## Git Workflow

### Pre-commit Hook

The `hooks/pre-commit` script (managed by github-control) runs:
1. Terraform formatting check (`terraform fmt -check -recursive`)
2. terraform-docs to update README.md (auto-stages changes)

### Commit Messages

Use conventional commits format (enforced by `hooks/commit-msg`):
- `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, etc.
- Generates changelog via git-cliff

## Module Version

The module version is defined in `locals.tf` as `local.module_version`. This should be tagged on a "main" resource in modules that use this module.