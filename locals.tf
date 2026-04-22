locals {
  module_version = "2.3.1"

  # Extract repos that have APT authentication configured (both machine and authFrom set)
  repo_pairs = [
    for name, repo in var.extra_repos : {
      machine  = repo.machine
      authFrom = repo.authFrom
    }
    if repo.machine != null && repo.authFrom != null
  ]

  repo_pairs_json = jsonencode(local.repo_pairs)

  # Generate APT preference files for repos with custom priority
  repo_preferences = [
    for name, repo in var.extra_repos : {
      content = templatefile("${path.module}/files/apt_preference.tpl", {
        origin   = regex("https?://([^/\\s]+)", repo.source)[0]
        priority = repo.priority
      })
      path        = "/etc/apt/preferences.d/${regex("https?://([^/\\s]+)", repo.source)[0]}.pref"
      permissions = "0644"
    }
    if repo.priority != null
  ]

  # Client packages needed for remote filesystem mounts. Index 2 of each
  # var.mounts entry is fs_vfstype (see cc_mounts documentation). We
  # inject the client package so `mount -a` does not fail on a base image
  # that does not ship nfs-common / cifs-utils.
  mount_client_packages = {
    nfs   = "nfs-common"
    nfs4  = "nfs-common"
    cifs  = "cifs-utils"
    smbfs = "cifs-utils"
  }

  mount_packages = distinct(compact([
    for m in var.mounts : lookup(local.mount_client_packages, length(m) >= 3 ? m[2] : "", "")
  ]))
}
