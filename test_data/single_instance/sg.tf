resource "aws_security_group" "instance" {
  description = "security group for test instance"
  name_prefix = "cloud-init-"
  vpc_id      = data.aws_subnet.current.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "ssh" {
  description       = "SSH access"
  security_group_id = aws_security_group.instance.id
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "icmp" {
  description       = "Allow all ICMP traffic"
  security_group_id = aws_security_group.instance.id
  from_port         = -1
  to_port           = -1
  ip_protocol       = "icmp"
  cidr_ipv4         = "0.0.0.0/0"
}


resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.instance.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
