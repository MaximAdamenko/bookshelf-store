#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run as root" >&2; exit 1; }
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

id -u bookshelf-ddns &>/dev/null || useradd --system --no-create-home \
  --shell "$(command -v nologin || echo /sbin/nologin)" bookshelf-ddns

install -m 755 "$here/desec-update.sh" /usr/local/bin/desec-update.sh
install -d -m 750 -o root -g bookshelf-ddns /etc/bookshelf

# Never overwrite a filled-in config: re-running this script must not wipe the
# token and silently strand DNS on a stale address.
if [[ ! -e /etc/bookshelf/desec.env ]]; then
  # A filled-in desec.env beside this script wins over the blank template, so
  # copying the repo to the instance is enough. It is gitignored either way.
  src=$here/desec.env.example
  [[ -e $here/desec.env ]] && src=$here/desec.env
  install -m 640 -o root -g bookshelf-ddns "$src" /etc/bookshelf/desec.env
  echo "created /etc/bookshelf/desec.env from $(basename "$src")"
  [[ $src == *.example ]] && echo "  -> fill in DESEC_DOMAIN and DESEC_TOKEN"
fi

install -m 644 "$here/bookshelf-ddns.service" "$here/bookshelf-ddns.timer" \
  /etc/systemd/system/
systemctl daemon-reload
systemctl enable bookshelf-ddns.service
# --now matters: enable alone only writes the boot symlink, so the 5-minute
# refresh stays dead until the next reboot. Found on the first live install.
systemctl enable --now bookshelf-ddns.timer

cat <<'EOF'

installed. next:
  1. edit /etc/bookshelf/desec.env
  2. systemctl start bookshelf-ddns.service
  3. journalctl -u bookshelf-ddns -n 20
  4. dig +short A <your-domain> @ns1.desec.io
EOF
