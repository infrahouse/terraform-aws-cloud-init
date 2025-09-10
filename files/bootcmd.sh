#!/usr/bin/env bash

source /etc/os-release
KEYRING_DIR="/etc/apt/keyrings"
KEYRING_PATH="${KEYRING_DIR}/infrahouse.gpg"
REPO_HOST="release-${UBUNTU_CODENAME}.infrahouse.com"
REPO_URL="https://${REPO_HOST}/"
REPO_LIST="/etc/apt/sources.list.d/50-infrahouse.list"

declare -A fingerprints=(
  [noble]="A627 B776 0019 0BA5 1B90  3453 D37A 181B 689A D619"
  [oracular]="3D44 6885 9E06 D0C6 EE54  5D23 6170 D0DB FAF6 E9F2"
)

if ! test -f $REPO_LIST
then
  install -d -m 0755 "${KEYRING_DIR}"
  tmpkey="$(mktemp)"
  EXPECTED_FINGERPRINT="${fingerprints[$UBUNTU_CODENAME]}"
  GPG_KEY="$(curl --fail --silent --show-error --location --retry 5 --connect-timeout 10 --max-time 30 \
    "${REPO_URL}DEB-GPG-KEY-release-${UBUNTU_CODENAME}.infrahouse.com")"
  echo "$GPG_KEY" | gpg --show-keys --fingerprint | grep -q "$EXPECTED_FINGERPRINT" || exit 1
  echo "$GPG_KEY" | gpg --dearmor > "${tmpkey}"
  install -m 0644 "${tmpkey}" "${KEYRING_PATH}"
  rm -f "${tmpkey}"
  echo "deb [signed-by=${KEYRING_PATH}] ${REPO_URL} ${UBUNTU_CODENAME} main" | tee "${REPO_LIST}" >/dev/null
fi
