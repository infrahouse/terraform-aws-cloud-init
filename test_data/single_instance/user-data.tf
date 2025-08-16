module "user-data" {
  source      = "./../../"
  environment = "development"
  role        = "base"
  post_runcmd = [
    "touch /tmp/puppet-done"
  ]
}
