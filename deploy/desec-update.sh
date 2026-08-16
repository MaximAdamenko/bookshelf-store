#!/usr/bin/env bash
set -euo pipefail

CONFIG=${BOOKSHELF_DDNS_CONFIG:-/etc/bookshelf/desec.env}
STATE_FILE=${STATE_DIRECTORY:-/var/lib/bookshelf-ddns}/last-ip
FORCE_AFTER=${DESEC_FORCE_AFTER_SECONDS:-86400}

[[ -r $CONFIG ]] || { echo "cannot read $CONFIG" >&2; exit 1; }
set -a; . "$CONFIG"; set +a
: "${DESEC_DOMAIN:?not set in $CONFIG}"
: "${DESEC_TOKEN:?not set in $CONFIG}"

imds() {
  local t
  t=$(curl -fsS --max-time 3 -X PUT \
        -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' \
        http://169.254.169.254/latest/api/token) || return 1
  curl -fsS --max-time 3 -H "X-aws-ec2-metadata-token: $t" \
       http://169.254.169.254/latest/meta-data/public-ipv4
}

# IMDS is the authority: it reports the address AWS actually attached, with no
# third party in the path. checkipv4 is the fallback for running this anywhere
# else, and only ever reports the address the packet left from -- which is the
# NAT gateway, not the instance, the moment there is one.
ip=$(imds || curl -fsS --max-time 5 https://checkipv4.dedyn.io/ || true)
ip=${ip//[$'\r\n ']/}

# This value is about to be pasted into a URL, so a malformed one is refused
# rather than sent. An empty answer means "no public IP", never "delete the record".
if [[ ! $ip =~ ^((25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})\.){3}(25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})$ ]]; then
  echo "no usable public IPv4 (got '${ip:-<empty>}') -- DNS left untouched" >&2
  exit 1
fi

mkdir -p "$(dirname "$STATE_FILE")"

now=$(date +%s)
if [[ -f $STATE_FILE ]]; then
  read -r seen_ip seen_at _ < "$STATE_FILE" || true
  if [[ ${seen_ip-} == "$ip" && $(( now - ${seen_at:-0} )) -lt $FORCE_AFTER ]]; then
    exit 0
  fi
fi

body=$(mktemp); trap 'rm -f "$body"' EXIT

# The token rides in a header, not ?password=: query strings land in `ps` output,
# in proxy logs, and in shell history. -G builds the query from the encoded pairs.
code=$(curl -sS --max-time 10 -o "$body" -w '%{http_code}' -G \
  -H "Authorization: Token $DESEC_TOKEN" \
  https://update.dedyn.io/ \
  --data-urlencode "hostname=$DESEC_DOMAIN" \
  --data-urlencode "myipv4=$ip" \
  --data-urlencode "myipv6=${DESEC_AAAA-}")

case $code in
  200) [[ $(< "$body") == good* || $(< "$body") == nochg* ]] \
         || { echo "deSEC returned 200 but said '$(< "$body")'" >&2; exit 1; } ;;
  401|403) echo "deSEC refused the token ($code) -- check DESEC_TOKEN and its A/AAAA policies" >&2; exit 1 ;;
  429)     echo "rate limited (2 updates per 2 min per domain) -- retrying next tick" >&2; exit 1 ;;
  *)       echo "deSEC update failed: HTTP $code $(< "$body")" >&2; exit 1 ;;
esac

printf '%s %s\n' "$ip" "$now" > "$STATE_FILE"
echo "$DESEC_DOMAIN -> $ip"
