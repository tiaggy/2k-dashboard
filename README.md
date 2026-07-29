# 2K Attendance Dashboard

A small web dashboard showing one combined calendar table per team, built from
the same Notion workspace the [2k-grouper](https://github.com/tiaggy/2k-grouper)
Telegram bot writes attendance to. The two projects only ever talk to each
other through Notion — this repo has no direct dependency on that one, just a
handful of shared Python modules copied in (see below).

A background loop re-derives every **not-approved** week from the live Notion
Capture Log on a timer. Approving a week freezes it (served from a local
SQLite cache, never recomputed) until it's un-approved again. While a week is
not approved, any day cell can be corrected by hand — this writes a real,
permanent change back to the Capture Log (the exact same database the bot
writes to), not a dashboard-only override.

## Auth model

Everything that touches real attendance data — viewing (`/api/data`),
approving/un-approving a week, and editing a day cell — requires the same
shared secret, sent as an `X-Approve-Token` header. The static page shell
(HTML/CSS/JS) loads without it; it carries no real data, just app code. If
`DASHBOARD_APPROVE_TOKEN` isn't set on the server, the dashboard has **no**
data access at all — it fails closed, not open.

The browser prompts for the token the first time it's needed and remembers it
in `localStorage`. There's one token for the whole dashboard: anyone who can
view it can also edit not-approved weeks. If you need to hand someone a
read-only link, that's not supported today — you'd need to add a separate
view-only token yourself.

## Setup

```bash
cp .env.example .env
# fill in NOTION_TOKEN and the four database ids, and DASHBOARD_APPROVE_TOKEN
```

See `.env.example` for what each variable is and where to find it. The four
Notion databases (Capture Log, Tracked Groups, Telegram Accounts, Week
Approvals) already exist for the 2k-grouper bot except Week Approvals, which
this dashboard owns — create it yourself with this schema before setting
`NOTION_APPROVALS_DB_ID`:

| Property | Type |
|---|---|
| Label | Title |
| Group | Relation → Tracked Groups |
| Week Start | Date |
| Approved | Checkbox |

## Running

```bash
docker compose up -d --build
docker compose logs -f
docker compose down             # state survives on the dashboard-state volume
```

Reachable at `http://127.0.0.1:8000` on the host it runs on.

## ⚠️ The Docker + UFW gotcha

On a Linux host, **Docker bypasses UFW.** Publishing a port
(`ports:` in compose) makes Docker write its own iptables rules that are
consulted *before* UFW's — so a port you think UFW is blocking is often
reachable from the internet anyway. `docker-compose.yml` binds this dashboard
to **loopback only** by default:

```yaml
ports:
  - "127.0.0.1:8000:8000"   # NOT reachable from outside this host, UFW or not
```

That's the safe default — nothing to firewall because nothing's exposed to
the network in the first place. To reach it from elsewhere, pick one:

**Just you, occasionally:**
```bash
ssh -L 8000:localhost:8000 you@your-server
# then open http://localhost:8000 on your own machine
```

**A team, over the internet:** put a real reverse proxy (Caddy, nginx) in
front, terminating TLS on 443 (which you *do* open in UFW) and proxying to
`127.0.0.1:8000`. The dashboard's own token gate is a shared secret, not a
substitute for TLS if you're exposing this beyond a loopback/SSH tunnel.

**A team, without exposing anything publicly:** put the host on a
[Tailscale](https://tailscale.com/) (or similar) network and change the
binding to `ports: ["8000:8000"]` — reachable only over the private mesh.

If you ever bind directly to `0.0.0.0` without one of the above in front,
treat that as equivalent to having no firewall on that port at all — Docker
makes it reachable regardless of any `ufw deny` you add. For UFW to actually
govern container ports, install
[`ufw-docker`](https://github.com/chaifeng/ufw-docker) instead of relying on
`ufw deny`.

## Layout

| File | What it is |
|---|---|
| `dashboard/server.py` | FastAPI app: background refresh loop, `/api/data`, `/api/approve`, `/api/edit-day` |
| `dashboard/notion_data.py` | Reads (groups, accounts, Capture Log records) — self-contained, doesn't assume any 2k-grouper-specific helpers |
| `dashboard/cache.py` | Local SQLite cache of computed week tables for approved (frozen) weeks |
| `dashboard/static/` | Vanilla HTML/JS/CSS frontend — no framework, no build step |
| `notion.py`, `notion_http.py` | Capture Log reads/writes + shared HTTP retry policy — copied from 2k-grouper as-is |
| `notionapprovals.py` | Reads/writes the Week Approvals database |
| `attendance.py` | Shared vocabulary: how a day's recorded intents collapse into one status code, and its color/legend |
| `config.py` | Env-var config — copied from 2k-grouper as-is, so it has some unused bot-only settings; harmless |

`notion.py`, `notion_http.py`, `attendance.py`, and `config.py` are **copies**,
not a shared package — if 2k-grouper changes one of these in a way that
matters here (a new Capture Log property, a retry-policy fix), it needs to be
applied to this repo's copy by hand. There's no automated sync.
