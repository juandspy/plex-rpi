# Plex Cleaner — Design

Date: 2026-09-21  
Status: approved for planning

## Goal

CLI on the Raspberry Pi host that finds media watched by a specific Plex user and optionally deletes those files (plus empty parent folders), then empties Plex trash and refreshes libraries.

Safe by default: dry-run unless `--delete` is passed.

## Context

- Stack: Docker Compose Plex (`jaymoulin/plex`, `network_mode: host`), media at `${MEDIA}` mounted as `/media` in the container.
- Plex container has no Python. Host has `python3` but not `plexapi`.
- Decision: run on the host with a small venv + `plexapi`.
- **Path remap (required):** Plex reports container paths under `/media/...`; the host sees `$MEDIA/...`. Roots and deletes use host paths. Remap with `--map /media:$MEDIA` (repeatable if needed). Apply remap to every Plex `location` before `--root` checks and deletes.

## Approach (chosen)

Single Python script using `plexapi`, adapted from a ChatGPT draft, with user-scoped watch filtering, empty-dir cleanup, and Plex trash/refresh after successful deletes.

Rejected: one-shot Docker Python container (heavier); bash + raw Plex XML API (fragile for per-user watched).

## Layout

```
scripts/plex-cleaner/
  plex_cleaner.py
  requirements.txt    # plexapi
  README.md           # token, setup, examples
```

## CLI

| Flag | Behavior |
|------|----------|
| `--root PATH` | Required for scan/delete (not for `--list-users`). Host dirs; only files under these are candidates. |
| `--map SRC:DST` | Required for scan/delete (not for `--list-users`). Remap Plex path prefix → host (e.g. `/media:$MEDIA`). |
| `--user NAME` | Required except with `--list-users`. Only items watched by this Plex account. |
| `--list-users` | Print Plex home/account users and exit. |
| `--movies` / `--tv` | If neither set, scan both. |
| `--delete` | Actually delete. Without it → dry-run. |
| `--dry-run` | Explicit dry-run. Mutually exclusive with `--delete` (error if both). |
| `--yes` | Skip interactive `DELETE` confirmation when deleting. |

Environment:

- `PLEX_URL` — default `http://localhost:32400`
- `PLEX_TOKEN` — required

Example:

```bash
export PLEX_TOKEN=...
# dry-run (default)
python3 plex_cleaner.py \
  --map "/media:$MEDIA" \
  --root "$MEDIA/movies" --root "$MEDIA/tv" \
  --user "Juan"

python3 plex_cleaner.py \
  --map "/media:$MEDIA" \
  --root "$MEDIA/movies" --root "$MEDIA/tv" \
  --user "Juan" --delete
```

## Behavior

### Discovery

1. Connect with `PlexServer(url, token)`.
2. Resolve `--user` against available Plex users (`--list-users` prints them).
3. For movie sections (if enabled): items watched by that user with `viewCount`/user history as exposed by plexapi for that account.
4. For show sections: watched episodes for that user.
5. For each item, take Plex `locations`, apply `--map` prefixes (longest match first), then keep only paths that exist on the host and are inside a `--root`.
6. Deduplicate by host path; sort by size descending; print report (title, host path, size, totals).

Watched = viewed by the selected user only (not any/all household users).

### Dry-run (default)

Print candidates and totals. Print how to re-run with `--delete`. Exit 0. No filesystem or Plex library mutations.

### Delete mode

1. Unless `--yes`, require typing `DELETE`.
2. For each candidate: `unlink` the file; then remove empty parent directories up to (but not including) the matching `--root`.
3. Per-file errors: log and continue.
4. If at least one file was deleted successfully: call `emptyTrash()` and refresh on each scanned library section.
5. Print deleted count and space freed.

## Error handling

- Missing `PLEX_TOKEN`, bad URL, missing `--root`, non-existent root → exit non-zero with clear message.
- Unknown `--user` → list available users and exit non-zero.
- `--delete` + `--dry-run` together → exit non-zero.
- Permission / missing file on delete → log, continue.

## Out of scope

- Cron / scheduled runs
- Min days since watched
- Exclude patterns / keep lists
- Multi-user “watched by everyone”
- Running inside the Plex container

## Success criteria

- Dry-run lists only media watched by the chosen user under `--root`.
- Without `--delete`, no files change and Plex libraries are untouched.
- With `--delete`, files and empty parents under roots are removed; Plex trash emptied and sections refreshed after successful deletes.
- `--list-users` is enough to discover the account name without reading Plex settings manually.
