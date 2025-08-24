#!/usr/bin/env bash

if command -v python3 >/dev/null 2>&1;  then
  py=python3;
elif command -v python >/dev/null 2>&1; then
  py=python;
else
  printf "%s\n" "$(date -Is) ERROR: Python not found. Use the InfraHouse AMI (includes Python) or preinstall Python before launch. Skipping secret resolution." \
    | tee /var/log/generate_apt_auth.log >/dev/null
    exit 0
fi
$py /usr/local/bin/generate_apt_auth.py /var/tmp/apt-auth.json >>/var/log/generate_apt_auth.log 2>&1
