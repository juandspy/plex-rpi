# Plex Cleaner

CLI on the Raspberry Pi host that finds media watched by a specific Plex user and optionally deletes those files (plus empty parent folders), then empties Plex trash and refreshes libraries.

**Safe by default:** dry-run unless `--delete` is passed.

## Setup

On Raspberry Pi OS you may need once:

```bash
sudo apt-get install -y python3-venv python3-pip
```

Then:

```bash
cd scripts/plex-cleaner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Plex token

1. Open Plex Web while signed in as the admin account.
2. Visit any library item, open XML view (or use [Plex support docs](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)).
3. Copy `X-Plex-Token` from the URL / headers.

```bash
export PLEX_TOKEN=...
# optional; defaults to http://localhost:32400
export PLEX_URL=http://localhost:32400
```

Plex inside Docker reports paths under `/media/...`. On the host those live under `$MEDIA`. Always pass `--map`.

```bash
export MEDIA=/media/hdd-1/my-media
```

## Usage

List home/account users:

```bash
python3 plex_cleaner.py --list-users
```

Dry-run (default):

```bash
python3 plex_cleaner.py \
  --map "/media:$MEDIA" \
  --root "$MEDIA/movies" --root "$MEDIA/series" \
  --user "juandspy"
```

Delete (asks you to type `DELETE` unless `--yes`):

```bash
python3 plex_cleaner.py \
  --map "/media:$MEDIA" \
  --root "$MEDIA/movies" --root "$MEDIA/tv" \
  --user "juandspy" --delete
```

### Flags

| Flag | Behavior |
|------|----------|
| `--root PATH` | Required for scan/delete. Host dirs; only files under these are candidates. |
| `--map SRC:DST` | Required for scan/delete. Remap Plex path prefix → host (e.g. `/media:$MEDIA`). |
| `--user NAME` | Required except with `--list-users`. |
| `--list-users` | Print users and exit. |
| `--movies` / `--tv` | If neither set, scan both. |
| `--delete` | Actually delete. Without it → dry-run. |
| `--dry-run` | Explicit dry-run. Error if combined with `--delete`. |
| `--yes` | Skip interactive `DELETE` confirmation. |
