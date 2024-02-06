
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
}
