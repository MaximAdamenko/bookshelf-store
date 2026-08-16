#!/usr/bin/env bash
# Mints a deSEC token scoped to the A and AAAA records of one domain, and nothing
# else. Run from your laptop, once. See README.md section 1.
set -euo pipefail

DOMAIN=${1-}
[[ -n $DOMAIN ]] || { echo "usage: $0 <domain>   e.g. $0 mybookshelfassignment.dedyn.io" >&2; exit 1; }
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }

API=https://desec.io/api/v1
TOKEN_NAME=bookshelf-ec2-ddns
ENV_FILE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/desec.env
BODY=$(mktemp)
LOGIN=

cleanup() {
  # The login token can manage tokens, so it is invalidated rather than left to
  # expire on its own.
  [[ -n $LOGIN ]] && curl -sS -X POST "$API/auth/logout/" \
    -H "Authorization: Token $LOGIN" -o /dev/null >/dev/null 2>&1 || true
  rm -f "$BODY"
}
trap cleanup EXIT

die() { echo "error: $*" >&2; exit 1; }

req() { # method path [json] -> prints HTTP code, body lands in $BODY
  local method=$1 path=$2 json=${3-}
  local args=(-sS -X "$method" -o "$BODY" -w '%{http_code}' -H 'Content-Type: application/json')
  [[ -n $LOGIN ]] && args+=(-H "Authorization: Token $LOGIN")
  if [[ -n $json ]]; then
    # --data-binary @- keeps the body off the command line: argv is world-readable
    # in `ps`, and on login this body contains the account password.
    printf '%s' "$json" | curl "${args[@]}" --data-binary @- "$API$path"
  else
    curl "${args[@]}" "$API$path"
  fi
}

detail() { jq -r '.detail // (. | tostring)' < "$BODY" 2>/dev/null || cat "$BODY"; }

echo "Scoping a new deSEC token to $DOMAIN"
echo "Your account password is used once, here, and never leaves this machine."
echo
read -rp  "deSEC account email: " EMAIL
read -rsp "deSEC account password: " PASSWORD; echo
echo

# Built with jq rather than string interpolation so a password containing quotes
# or backslashes cannot produce malformed JSON. Passed through the environment,
# not argv, for the same reason as --data-binary above.
login_json=$(EMAIL="$EMAIL" PASSWORD="$PASSWORD" jq -n '{email: env.EMAIL, password: env.PASSWORD}')
unset PASSWORD

code=$(req POST /auth/login/ "$login_json")
[[ $code == 200 ]] || die "login failed (HTTP $code): $(detail)"
LOGIN=$(jq -r .token < "$BODY")
echo "logged in"

code=$(req GET /auth/tokens/)
[[ $code == 200 ]] || die "could not list tokens (HTTP $code): $(detail)"
if [[ $(jq --arg n "$TOKEN_NAME" '[.[] | select(.name==$n)] | length' < "$BODY") != 0 ]]; then
  echo
  echo "A token named '$TOKEN_NAME' already exists. Creating another is harmless"
  echo "but leaves clutter you will have to tell apart later."
  read -rp "Create a second one anyway? [y/N] " a
  [[ $a == [yY] ]] || die "stopped. Delete the old token in the deSEC UI first, or rename this one."
fi

# max_unused_period: an abandoned token expires itself rather than lingering.
code=$(req POST /auth/tokens/ \
  "$(jq -n --arg n "$TOKEN_NAME" '{name: $n, max_unused_period: "90 00:00:00"}')")
[[ $code == 201 ]] || die "token creation failed (HTTP $code): $(detail)"
TOKEN_ID=$(jq -r .id < "$BODY")
NEW_TOKEN=$(jq -r .token < "$BODY")
echo "created token $TOKEN_ID (expires if unused for $(jq -r '.max_unused_period // "never"' < "$BODY"))"

# The default policy must exist before any specific one, and denies everything
# the two policies below do not explicitly allow.
code=$(req POST "/auth/tokens/$TOKEN_ID/policies/rrsets/" \
  '{"domain":null,"subname":null,"type":null,"perm_write":false}')
[[ $code == 201 ]] || die "default-deny policy failed (HTTP $code): $(detail)"
echo "default policy: deny"

# Both types are required. A dynDNS update also *removes* the AAAA RRset, so a
# token allowed only A gets a 403 on every call.
for t in A AAAA; do
  code=$(req POST "/auth/tokens/$TOKEN_ID/policies/rrsets/" \
    "$(jq -n --arg d "$DOMAIN" --arg t "$t" \
       '{domain: $d, subname: "", type: $t, perm_write: true}')")
  [[ $code == 201 ]] || die "$t policy failed (HTTP $code): $(detail)"
  echo "allowed: write $t on $DOMAIN"
done

echo
echo "policies now on this token:"
code=$(req GET "/auth/tokens/$TOKEN_ID/policies/rrsets/")
[[ $code == 200 ]] || die "could not read policies back (HTTP $code): $(detail)"
jq -r '.[] | "  \(.domain // "*")  subname=\(.subname // "*")  type=\(.type // "*")  write=\(.perm_write)"' < "$BODY"

# Proves the token authenticates. The write path is only proven by the first real
# update from the instance -- doing one here would point DNS at this laptop.
auth_code=$(curl -sS -o /dev/null -w '%{http_code}' \
  -H "Authorization: Token $NEW_TOKEN" "$API/domains/$DOMAIN/rrsets/")
echo
echo "token authenticates against $DOMAIN: HTTP $auth_code"

echo
echo "================ token secret, shown once ================"
echo "$NEW_TOKEN"
echo "========================================================="

if [[ -f $ENV_FILE ]]; then
  echo
  read -rp "Write it into $(basename "$ENV_FILE") now? [y/N] " a
  if [[ $a == [yY] ]]; then
    # 600 is set explicitly, not inherited: this backup holds the old token, and
    # cp -p would happily carry over a loose mode from the source.
    cp "$ENV_FILE" "$ENV_FILE.bak"
    chmod 600 "$ENV_FILE.bak"
    tmp=$(mktemp)
    # awk, not sed: a replacement string goes in verbatim, with no metacharacters
    # to escape and no risk of mangling the rest of the file.
    awk -v tok="$NEW_TOKEN" -v dom="$DOMAIN" '
      /^DESEC_TOKEN=/  {print "DESEC_TOKEN=" tok; next}
      /^DESEC_DOMAIN=/ {print "DESEC_DOMAIN=" dom; next}
      {print}' "$ENV_FILE" > "$tmp"
    cat "$tmp" > "$ENV_FILE"
    rm -f "$tmp"
    chmod 600 "$ENV_FILE"
    echo "updated $ENV_FILE (previous kept as $(basename "$ENV_FILE").bak -- delete it once this works)"
  fi
fi

echo
echo "next: copy deploy/ to the instance and run install.sh (README.md section 2)"
