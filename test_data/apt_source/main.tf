module "test" {
  source      = "../../"
  environment = "dev"
  role        = "foo"
  extra_repos = {
    "test-repo" = {
      source    = "deb [signed-by=$KEY_FILE] https://example.com/ubuntu noble main"
      keyid     = "A627B7760019BA51B903453D37A181B689AD619"
      keyserver = "keyserver.ubuntu.com"
    }
  }
}
