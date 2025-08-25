
module "test" {
  source      = "../../"
  environment = "dev"
  role        = "foo"
  extra_repos = {
    "foo" : {
      source : "deb [signed-by=$KEY_FILE] foo main"
      key : "bar"
    }
    "bar" : {
      source : "deb [signed-by=$KEY_FILE] bar main"
      key : "key-bar"
      ## machine as in ~/.netrc
      ## instead of login/password in plaintext - a secret ARN with a JSON like
      /*
          {
            "apt": "debian"
          }
       */
      machine : "bar"
      authFrom : "bar-secret-arn"
    }
  }
  puppet_manifest = var.puppet_manifest
}
