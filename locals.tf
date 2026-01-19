locals {
  module_version = "2.2.2"

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
}
