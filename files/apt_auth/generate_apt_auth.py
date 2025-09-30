import json
import sys

import boto3


def generate_apt_auth(auth_inputs):
    client = boto3.client("secretsmanager")
    with open("/etc/apt/auth.conf.d/50user", "w", encoding="utf-8") as auth_fp:
        with open(auth_inputs, "r", encoding="utf-8") as f:
            for pair in json.load(f):
                machine = pair["machine"]
                auth_from = pair["authFrom"]
                auth = json.loads(client.get_secret_value(SecretId=auth_from)["SecretString"])
                login = list(auth.keys())[0]
                password = auth[login]
                auth_fp.write(f"machine {machine} login {login} password {password}\n")


if __name__ == "__main__":
    generate_apt_auth(sys.argv[1])
