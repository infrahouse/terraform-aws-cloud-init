locals {
  module_version = "2.0.0"

  repo_pairs = [
    for name in sort(keys(var.extra_repos)) : {
      machine  = try(var.extra_repos[name].machine, null)
      authFrom = try(var.extra_repos[name].authFrom, null)
    }
    if try(var.extra_repos[name].machine, null) != null
    && try(var.extra_repos[name].authFrom, null) != null
  ]

  repo_pairs_json = jsonencode(local.repo_pairs)
}
