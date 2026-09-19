# Backups

Nightly backup of everything needed to fully recover the service:

- Postgres database (`pg_dump`, custom format)
- `media/` volume (uploaded audio + album art)
- Navidrome's sqlite database at `/opt/docker-apps/navidrome/data` (its `cache/`
  subdirectory is excluded — it's regenerable and not needed for recovery)

All three are pushed to a single [restic](https://restic.net/) repository on
Backblaze B2. Restic handles encryption, deduplication and retention pruning,
so only changed data is uploaded after the first run.

On every run (success or failure), an email is sent via the app's own Gmail
SMTP credentials with the run's log attached.

## One-time setup (on the production host)

1. Install restic and curl: `apt install restic curl`.
2. In the B2 console, create a bucket (private) and an application key scoped
   to just that bucket.
3. `cp backup.env.example backup.env` and fill in:
   - `B2_ACCOUNT_ID` / `B2_ACCOUNT_KEY` — the B2 key
   - `RESTIC_REPOSITORY` — `b2:<bucket-name>:cmn-artist`
   - `RESTIC_PASSWORD` — generate with `openssl rand -base64 32` and save it
     in a password manager. **This is not recoverable if lost** — losing it
     means losing the backups even though the encrypted data is still in B2.
   - `PROJECT_DIR`, `MEDIA_DIR`, `NAVIDROME_DATA_DIR` — host paths
   - `DBUSER` / `DBNAME` / `DBPASS` — must match `docker-compose.yml`
   - `NOTIFY_EMAIL` — where to send success/failure notifications
   - `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `DEFAULT_FROM_EMAIL` — same
     Gmail app credentials as the app's own `.env`. Leave `NOTIFY_EMAIL` blank
     to skip notifications entirely.
4. `chmod 600 backup.env` (contains secrets).
5. Initialize the repository (one-time): `restic init` (with the env vars
   from `backup.env` exported, or just run `env $(cat backup.env | xargs)
   restic init`).
6. Install the systemd units:
   ```sh
   sudo cp cmn-backup.service cmn-backup.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now cmn-backup.timer
   ```
   Adjust `ExecStart` in `cmn-backup.service` first if the repo isn't at
   `/opt/docker-apps/cmn_artist`.
7. Test it: `sudo systemctl start cmn-backup.service` then
   `journalctl -u cmn-backup.service -f`.

Runs nightly at 03:00 (server time), ±15 min jitter. `Persistent=true` means
a missed run (e.g. host was down) fires as soon as the system is back up.

## Monitoring

You should get an email every night either way (see above). If a run fails
before the point where `notify()` can send mail (e.g. the machine is down, or
`backup.env` itself is missing), that silence is itself the signal — nothing
watches for a *missing* email. Check status manually any time:

```sh
systemctl status cmn-backup.timer
journalctl -u cmn-backup.service --since -7d
```

## Restoring

```sh
./restore.sh list
./restore.sh restore <snapshot-id> /tmp/cmn-restore
```

This restores the raw files into a target directory:

- `/tmp/cmn-restore/tmp/tmp.XXXXXX/postgres-postgres.dump` — the pg_dump file
- `/tmp/cmn-restore/<MEDIA_DIR>` — the media directory tree
- `/tmp/cmn-restore/<NAVIDROME_DATA_DIR>` — Navidrome's data directory

From there:

**Postgres:**
```sh
docker compose exec -T postgres pg_restore -U admin -d postgres --clean --if-exists < postgres-postgres.dump
```

**Media:** stop the app, replace the `media/` directory contents with the
restored tree, restart.

**Navidrome:** stop Navidrome, replace `/opt/docker-apps/navidrome/data`
(minus `cache/`, which will regenerate) with the restored tree, restart.

Always restore to a scratch location and verify before touching production
data.
