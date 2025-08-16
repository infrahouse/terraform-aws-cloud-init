resource "tls_private_key" "cloud-init-test" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "cloud-init-test" {
  key_name_prefix = "cloud-init-test"
  public_key      = tls_private_key.cloud-init-test.public_key_openssh
}
