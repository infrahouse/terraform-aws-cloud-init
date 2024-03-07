
module "test" {
  source      = "../../"
  environment = "dev"
  role        = "foo"
  extra_repos = {
    "foo" : {
      source : "deb [signed-by=$KEY_FILE] foo main"
      key : "bar"
    }
  }
  extra_files = [
    {
      content : "foo content"
      path : "/tmp/foo"
      permissions : "0600"
    }
  ]
  custom_facts = {
    "foo" : "bar"
    "foo_map" : {
      "foo" : "bar"
    }
  }
  mounts = var.mounts
  ssh_host_keys = [
    {
      type : "rsa"
      private : file("${path.module}/ssh_keys/ssh_host_rsa_key")
      public : file("${path.module}/ssh_keys/ssh_host_rsa_key.pub")
    }
  ]
  puppet_manifest = "/var/log/foo"
}
