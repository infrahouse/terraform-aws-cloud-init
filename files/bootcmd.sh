#!/usr/bin/env bash
set -euo pipefail

source /etc/os-release
KEYRING_DIR="/etc/apt/keyrings"
KEYRING_PATH="${KEYRING_DIR}/infrahouse.gpg"
REPO_HOST="release-${UBUNTU_CODENAME}.infrahouse.com"
REPO_URL="https://${REPO_HOST}/"
REPO_LIST="/etc/apt/sources.list.d/50-infrahouse.list"

if ! test -f $REPO_LIST
then
  install -d -m 0755 "${KEYRING_DIR}"
  tmpkey="$(mktemp)"
  # Fetch the (possibly multi-key) armored bundle over HTTPS from our own repo
  # host. gpg --dearmor handles concatenated keys, so a rotation-overlap bundle
  # holding both the outgoing and incoming keys installs cleanly. Trust is
  # anchored on TLS to release-<codename>.infrahouse.com; rotation is entirely
  # server-side (see issue #89). Fetch before touching the keyring; under
  # `set -euo pipefail` any failure here (curl --fail, gpg --dearmor, install)
  # aborts before we write REPO_LIST, rather than leaving a broken keyring that
  # only surfaces later at apt-get update.
  GPG_KEY="$(curl --fail --silent --show-error --location --retry 5 --connect-timeout 10 --max-time 30 \
    "${REPO_URL}DEB-GPG-KEY-release-${UBUNTU_CODENAME}.infrahouse.com")"
  echo "$GPG_KEY" | gpg --dearmor > "${tmpkey}"
  install -m 0644 "${tmpkey}" "${KEYRING_PATH}"
  rm -f "${tmpkey}"
  echo "deb [signed-by=${KEYRING_PATH}] ${REPO_URL} ${UBUNTU_CODENAME} main" | tee "${REPO_LIST}" >/dev/null
fi
