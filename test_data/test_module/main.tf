
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
  mounts = [
    [
      "file_system_id.efs.aws-region.amazonaws.com:/",
      "mount_point",
      "nfs4",
      "nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev",
      "0",
      "0"
    ],
    ["xvdh", "/opt/data", "auto", "defaults,nofail", "0", "0"]
  ]
  ssh_host_keys = [
    {
      type : "rsa"
      private : file("${path.module}/ssh_keys/ssh_host_rsa_key")
      public : file("${path.module}/ssh_keys/ssh_host_rsa_key.pub")
    }
  ]
  puppet_manifest = "/var/log/foo"
}
