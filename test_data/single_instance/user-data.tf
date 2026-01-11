module "user-data" {
  source      = "./../../"
  environment = "development"
  role        = "base"
  post_runcmd = [
    "touch /tmp/puppet-done"
  ]
  extra_repos = {
    "fake" : {
      source : "deb https://us.archive.ubuntu.com/ubuntu $RELEASE main"
      key : file("${path.module}/files/DEB-GPG-KEY-infrahouse-noble")
      machine : "us.archive.ubuntu.com"
      authFrom : module.debian-auth.secret_arn
    }
  }
}

module "debian-auth" {
  source             = "registry.infrahouse.com/infrahouse/secret/aws"
  version            = "1.1.1"
  environment        = "development"
  secret_description = ""
  secret_name        = "debian-repo-http-auth"
  secret_value = jsonencode(
    {
      "foo" : "bar"
    }
  )
  readers = [
    module.instance-profile.instance_role_arn
  ]
}
