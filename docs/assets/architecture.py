#!/usr/bin/env python3
"""
Generate architecture diagram for terraform-aws-cloud-init module.

This diagram shows the cloud-init bootstrap flow for EC2 instances.

Requirements:
    pip install diagrams

Usage:
    python architecture.py

Output:
    architecture.png (in current directory)
"""
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.security import SecretsManager
from diagrams.generic.storage import Storage
from diagrams.onprem.iac import Terraform

fontsize = "14"

# Match MkDocs Material theme fonts (Roboto)
graph_attr = {
    "splines": "spline",
    "nodesep": "1.5",
    "ranksep": "1.5",
    "fontsize": fontsize,
    "fontname": "Roboto",
    "dpi": "200",
}

node_attr = {
    "fontname": "Roboto",
    "fontsize": fontsize,
}

edge_attr = {
    "fontname": "Roboto",
    "fontsize": fontsize,
}

with Diagram(
    "Cloud-Init Bootstrap Flow",
    filename="architecture",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
    outformat="png",
):
    # Terraform generates userdata
    terraform = Terraform("\nTerraform\nModule")

    with Cluster("AWS Account"):
        # Secrets Manager for APT auth
        secrets = SecretsManager("\nSecrets Manager\n(APT credentials)")

        with Cluster("EC2 Instance"):
            ec2 = EC2("\nLaunch")

            with Cluster("Cloud-Init Phases"):
                bootcmd = Storage("\n1. bootcmd\nAPT repos, GPG keys")
                write_files = Storage("\n2. write_files\nAWS config, Puppet facts")
                packages = Storage("\n3. packages\npuppet-code, toolkit")
                runcmd = Storage("\n4. runcmd\nih-puppet apply")

            puppet_done = Storage("\npuppet-done\nmarker")

    # Connections
    terraform >> Edge(label="userdata (base64)") >> ec2
    ec2 >> bootcmd >> write_files >> packages >> runcmd >> puppet_done

    # Secrets flow
    secrets >> Edge(style="dashed") >> bootcmd