# deploy — dynamic DNS for the EC2 instance

The instance's public IPv4 changes every time it is stopped and started. This keeps a
free deSEC (`dedyn.io`) hostname pointed at whatever the current address is, which is
also what makes TLS possible at all: Let's Encrypt will not issue a certificate for a
bare IP.

Runs on the **host**, not in Docker. The hostname has to be correct independently of
whether the app stack is healthy — if the updater were a compose service and the stack
failed to come up, you would lose the ability to reach the box by name to debug it.

```
desec-update.sh          the updater
bookshelf-ddns.service   oneshot, hardened, runs at boot
bookshelf-ddns.timer     every 5 min with jitter
desec.env.example        template for /etc/bookshelf/desec.env
install.sh               idempotent installer          (run on the instance)
scope-token.sh           mints a least-privilege token (run on your laptop)
```

Note that nothing here is a container. `deploy/` is host-level systemd that runs
*alongside* `docker compose`, so the hostname stays correct even when the app stack is
down — which is exactly when you need to reach the box by name.

---

## The four values, and which one is secret

| Value | Example | Used for | Secret? |
|---|---|---|---|
| Account email + password | `you@example.com` / … | Logging into desec.io, minting tokens | **Yes — never put this on the instance** |
| Domain (= dyndns2 "username") | `mybookshelfassignment.dedyn.io` | The `hostname` parameter | No, it is public DNS |
| **Token secret** (= dyndns2 "password") | `mu4W4MHuSc0Hy-GD1h_dnKuZBond` | `Authorization: Token …` | **Yes. This is the one** |
| Update URL | `https://update.dedyn.io/` | The endpoint | No |

deSEC's docs describe a *router* setup, because the usual case is a home network where
the router owns the changing address. On EC2 there is no router in the path — the
instance holds the public IP, so the instance is the dynDNS client. That is what
`desec-update.sh` is; the router section of their docs does not apply.

The account password is only ever used from your laptop, once, to mint the scoped token
below. If it reached the instance, a compromise of the box would cost the whole deSEC
account instead of one A record.

---

## 1. deSEC side (from your laptop, once)

Sign up at <https://desec.io/> and create the dynDNS domain, then mint a **scoped** token.
The web UI creates tokens but not policies, so this part is the REST API.

The token deSEC hands you at signup works, but it is unrestricted — it can rewrite every
record in your account. Scoping is optional hardening, not a requirement to function.

```bash
./scope-token.sh mybookshelfassignment.dedyn.io
```

It prompts for your account email and password (used once, never stored), mints a token,
applies the three policies below, reads them back so you can see what was set, and offers
to write the secret into `desec.env`. The old file is kept as `desec.env.bak` at mode
`600` — delete it once the new token is confirmed working.

Prefer a fresh token over adding policies to your signup token: if the policies come out
wrong, the unrestricted one is still there as a way back in.

<details>
<summary>What the script does, if you would rather run it by hand</summary>

```bash
DOMAIN=mybookshelfassignment.dedyn.io

LOGIN=$(curl -sS https://desec.io/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"..."}' | jq -r .token)

# max_unused_period: an abandoned token expires itself
read TOKEN_ID DESEC_TOKEN < <(curl -sS https://desec.io/api/v1/auth/tokens/ \
  -H "Authorization: Token $LOGIN" -H 'Content-Type: application/json' \
  -d '{"name":"bookshelf-ec2-ddns","max_unused_period":"90 00:00:00"}' \
  | jq -r '.id + " " + .token')

# default deny first -- deSEC requires it before any specific policy exists
curl -sS https://desec.io/api/v1/auth/tokens/$TOKEN_ID/policies/rrsets/ \
  -H "Authorization: Token $LOGIN" -H 'Content-Type: application/json' \
  -d '{"domain":null,"subname":null,"type":null,"perm_write":false}'

# then exactly the two RRsets the updater touches
for t in A AAAA; do
  curl -sS https://desec.io/api/v1/auth/tokens/$TOKEN_ID/policies/rrsets/ \
    -H "Authorization: Token $LOGIN" -H 'Content-Type: application/json' \
    -d "{\"domain\":\"$DOMAIN\",\"subname\":\"\",\"type\":\"$t\",\"perm_write\":true}"
done

echo "$DESEC_TOKEN"   # the only time you will see it
```

</details>

**Both A and AAAA are required.** A dynDNS update potentially writes *and removes* the
AAAA RRset, so a token scoped to A alone gets a 403 on every call.

Why scope it at all: the same least-privilege reasoning as the `bookshelf_app` database
role in `SECURITY.md` §2.6. A leaked token can then rewrite one address record and
nothing else — it cannot delete the domain, touch other records, or manage tokens.

`allowed_subnets` is deliberately *not* used. Pinning the token to the instance's IP
would be self-defeating when the whole point is that the IP changes.

## 2. Instance side

```bash
sudo ./deploy/install.sh
sudo vi /etc/bookshelf/desec.env       # DESEC_DOMAIN, DESEC_TOKEN
sudo systemctl start bookshelf-ddns.service
journalctl -u bookshelf-ddns -n 20
```

The config lands at `/etc/bookshelf/desec.env`, mode `0640`, owner `root:bookshelf-ddns`
— readable by the service user, by nobody else, and never by the containers.

### Where the token must not go

- **Not in EC2 user-data.** Readable via IMDS by anything on the box, including a
  compromised container, and visible to anyone with `ec2:DescribeInstanceAttribute`.
- **Not in `Server/.env`.** That file becomes the backend container's environment, so
  every Python dependency in the image can read it via `os.environ`. Different
  credential, different lifetime, different reader — different file.
- **Not in `docker-compose.yml`**, not baked into an AMI, and not as a `?password=`
  query parameter (which is why the updater uses the `Authorization` header).

## 3. Verify

```bash
dig +short A    mybookshelfassignment.dedyn.io @ns1.desec.io   # the instance IP
dig +short AAAA mybookshelfassignment.dedyn.io @ns1.desec.io   # empty
systemctl list-timers bookshelf-ddns.timer
```

The test that actually matters: **stop and start the instance**, then watch the A record
follow the new address within a few minutes.

---

## How it behaves

**Address source.** IMDSv2 (`/latest/meta-data/public-ipv4`) is the authority — it
reports what AWS actually attached, instantly, with no third party in the path. If IMDS
is unreachable the script falls back to `https://checkipv4.dedyn.io/`, which reports the
address the packet left from; that is the same thing on a plain EC2 instance and the
wrong thing behind a NAT gateway.

**Call volume.** The last published address is cached in
`/var/lib/bookshelf-ddns/last-ip`. The API is called only when the address changed, or
once every 24 h as a guard against silent drift. deSEC allows **2 updates per 2 minutes
per domain**, so the 5-minute timer has a wide margin even if the address flaps.

**AAAA.** `DESEC_AAAA` is empty by default, which deletes the AAAA record on every
update. That is intentional for an IPv4-only instance: a stale AAAA makes IPv6 clients
try that address first and hang before falling back. Set it to `preserve` once the
instance really has IPv6.

**Failure is loud and safe.** A malformed or empty address is refused rather than sent —
an empty answer means "no public IP", never "delete the record". Non-200 responses are
reported by class (401/403 token, 429 rate limit, anything else verbatim) and the state
file is left untouched, so the next tick retries.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `deSEC refused the token (403)` | Policies missing the `AAAA` RRset, or `subname` not `""` |
| `deSEC refused the token (401)` | Wrong `DESEC_TOKEN`, or it hit `max_unused_period` |
| `rate limited` | More than 2 updates in 2 min for that domain |
| `no usable public IPv4` | Instance has no public IP, or IMDS is disabled and egress is blocked |
| Unit runs but DNS is stale | Cached — `sudo rm /var/lib/bookshelf-ddns/last-ip` and start the unit |

## Security group

Inbound `80` and `443` from `0.0.0.0/0`, `22` from your address only. Outbound `443`
must be open — the updater talks to `update.dedyn.io`. IMDS is link-local and needs no
rule.

## Next: TLS

With a resolving hostname the remaining blocker from session 12 is gone. Certificates go
through HTTP-01 via webroot (port 80 is already open and nginx is already the entry
point), so this token stays scoped to A/AAAA and never needs TXT write. A wildcard
certificate would need DNS-01 and a second scoped token — a new token, not a widening of
this one.
