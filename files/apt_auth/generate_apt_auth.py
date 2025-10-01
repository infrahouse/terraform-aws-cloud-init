import json
import os
import sys

import boto3


def generate_apt_auth(auth_inputs):
    client = boto3.client("secretsmanager")
    auth_file = "/etc/apt/auth.conf.d/50user"
    with open(auth_file, "w", encoding="utf-8") as auth_fp:
        with open(auth_inputs, "r", encoding="utf-8") as f:
            for pair in json.load(f):
                machine = pair["machine"]
                auth_from = pair["authFrom"]
                auth = json.loads(client.get_secret_value(SecretId=auth_from)["SecretString"])
                login = list(auth.keys())[0]
                password = auth[login]
                auth_fp.write(f"machine {machine} login {login} password {password}\n")
    # Set permissions to 600 (rw-------) to protect passwords
    os.chmod(auth_file, 0o600)


if __name__ == "__main__":
    generate_apt_auth(sys.argv[1])
