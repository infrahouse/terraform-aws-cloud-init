locals {
  module_version = "2.2.1"

  repo_pairs = [
    for name in sort(keys(var.extra_repos)) : {
      machine  = try(var.extra_repos[name].machine, null)
      authFrom = try(var.extra_repos[name].authFrom, null)
    }
    if try(var.extra_repos[name].machine, null) != null
    && try(var.extra_repos[name].authFrom, null) != null
  ]

  repo_pairs_json = jsonencode(local.repo_pairs)
  repo_preferences = [
    for name, repo in var.extra_repos : {
      content = templatefile("${path.module}/files/apt_preference.tpl", {
        origin   = regex("https?://([^/\\s]+)", repo.source)[0]
        priority = repo.priority
      })
      path        = "/etc/apt/preferences.d/${regex("https?://([^/\\s]+)", repo.source)[0]}.pref"
      permissions = "0644"
    }
    if try(repo.priority, null) != null
  ]
}
