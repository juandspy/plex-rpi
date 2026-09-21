#!/usr/bin/env python3
"""Delete (or dry-run) Plex media watched by a specific user under host roots."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Candidate:
    title: str
    host_path: Path
    size: int
    root: Path
    section_title: str


def parse_map(spec: str) -> tuple[str, str]:
    if ":" not in spec:
        raise argparse.ArgumentTypeError(f"--map expects SRC:DST, got {spec!r}")
    src, dst = spec.split(":", 1)
    if not src or not dst:
        raise argparse.ArgumentTypeError(f"--map expects SRC:DST, got {spec!r}")
    return src.rstrip("/"), str(Path(dst).expanduser())


def remap_path(plex_path: str, maps: Sequence[tuple[str, str]]) -> str:
    """Apply longest matching SRC prefix; return host path (or original if no match)."""
    best: tuple[str, str] | None = None
    for src, dst in maps:
        if plex_path == src or plex_path.startswith(src + "/"):
            if best is None or len(src) > len(best[0]):
                best = (src, dst)
    if best is None:
        return plex_path
    src, dst = best
    rest = plex_path[len(src) :].lstrip("/")
    return str(Path(dst) / rest) if rest else dst


def under_root(host_path: str, roots: Sequence[Path]) -> Path | None:
    """Return the matching root Path if host_path is inside it, else None."""
    try:
        resolved = Path(host_path).resolve()
    except OSError:
        return None
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return root
        except ValueError:
            continue
    return None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Clean watched Plex media for one user")
    p.add_argument("--root", action="append", default=[], help="Host root dir (repeatable)")
    p.add_argument(
        "--map",
        dest="maps",
        action="append",
        type=parse_map,
        default=[],
        help="Plex path prefix:host path (repeatable)",
    )
    p.add_argument("--user", help="Plex username to filter watched items")
    p.add_argument("--list-users", action="store_true", help="Print users and exit")
    p.add_argument("--movies", action="store_true", help="Scan movie libraries only")
    p.add_argument("--tv", action="store_true", help="Scan TV libraries only")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--delete", action="store_true", help="Actually delete files")
    g.add_argument("--dry-run", action="store_true", help="Explicit dry-run (default)")
    p.add_argument("--yes", action="store_true", help="Skip DELETE confirmation")
    p.add_argument(
        "--url",
        default=os.environ.get("PLEX_URL", "http://localhost:32400"),
        help="Plex URL (default: $PLEX_URL or http://localhost:32400)",
    )
    p.add_argument(
        "--token",
        default=os.environ.get("PLEX_TOKEN"),
        help="Plex token (default: $PLEX_TOKEN)",
    )
    return p.parse_args(argv)


def connect(url: str, token: str):
    try:
        from plexapi.server import PlexServer
    except ImportError:
        print(
            "error: plexapi not installed. Run: pip install -r requirements.txt",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return PlexServer(url, token)


def list_user_names(plex) -> list[str]:
    names: list[str] = []
    try:
        account = plex.myPlexAccount()
        names.append(account.username)
        for u in account.users():
            print("Found user:", u.title, u.username, file=sys.stderr)
            names.append(u.title or u.username)
    except Exception:
        print("error: cannot get users using plex.myPlexAccount")
        for a in plex.systemAccounts():
            if a.name and a.name != "Shared":
                print("Found user:", a.name, file=sys.stderr)
                names.append(a.name)
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def resolve_user(plex, name: str) -> str:
    available = list_user_names(plex)
    lower = {n.lower(): n for n in available}
    if name.lower() not in lower:
        print(f"error: unknown user {name!r}. Available:", file=sys.stderr)
        for n in available:
            print(f"  {n}", file=sys.stderr)
        raise SystemExit(1)
    return lower[name.lower()]


def section_types(args: argparse.Namespace) -> set[str]:
    if args.movies and not args.tv:
        return {"movie"}
    if args.tv and not args.movies:
        return {"show"}
    return {"movie", "show"}


def item_title(item) -> str:
    title = getattr(item, "title", str(item))
    grandparent = getattr(item, "grandparentTitle", None)
    season_ep = getattr(item, "seasonEpisode", None)
    if grandparent and season_ep:
        return f"{grandparent} - {season_ep} - {title}"
    return title


def iter_watched_items(user_plex, types: set[str]):
    for section in user_plex.library.sections():
        if section.type == "movie" and "movie" in types:
            for item in section.search(unwatched=False):
                yield section, item
        elif section.type == "show" and "show" in types:
            # TODO: don't delete episodes if the season is not watched
            for show in section.all():
                for ep in show.watched():
                    yield section, ep


def collect_candidates(
    user_plex,
    maps: Sequence[tuple[str, str]],
    roots: Sequence[Path],
    types: set[str],
) -> list[Candidate]:
    by_path: dict[Path, Candidate] = {}
    for section, item in iter_watched_items(user_plex, types):
        locations: Iterable[str] = getattr(item, "locations", None) or []
        title = item_title(item)
        for loc in locations:
            host = Path(remap_path(loc, maps))
            root = under_root(str(host), roots)
            if root is None:
                continue
            if not host.is_file():
                continue
            try:
                size = host.stat().st_size
            except OSError:
                continue
            resolved = host.resolve()
            by_path[resolved] = Candidate(title, resolved, size, root, section.title)
    return sorted(by_path.values(), key=lambda c: c.size, reverse=True)


def format_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def print_report(cands: list[Candidate], dry_run: bool) -> None:
    total = sum(c.size for c in cands)
    for c in cands:
        print(f"{format_size(c.size):>12}  {c.title}")
        print(f"              {c.host_path}")
    print(f"\n{len(cands)} file(s), {format_size(total)} total")
    if dry_run:
        print("\nDry-run only. Re-run with --delete to remove these files.")


def remove_empty_parents(path: Path, root: Path) -> None:
    parent = path.parent
    root_r = root.resolve()
    while True:
        try:
            parent_r = parent.resolve()
            parent_r.relative_to(root_r)
        except (OSError, ValueError):
            break
        if parent_r == root_r:
            break
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def delete_candidates(cands: list[Candidate]) -> tuple[int, int]:
    deleted, freed = 0, 0
    for c in cands:
        try:
            c.host_path.unlink()
            deleted += 1
            freed += c.size
            remove_empty_parents(c.host_path, c.root)
            print(f"deleted {c.host_path}")
        except OSError as e:
            print(f"error deleting {c.host_path}: {e}", file=sys.stderr)
    return deleted, freed


def refresh_after_delete(admin_plex, section_titles: set[str]) -> None:
    for section in admin_plex.library.sections():
        if section.title in section_titles:
            section.emptyTrash()
            section.update()


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.token:
        print("error: PLEX_TOKEN required (env or --token)", file=sys.stderr)
        return 1

    try:
        plex = connect(args.url, args.token)
    except Exception as e:
        print(f"error: cannot connect to Plex at {args.url}: {e}", file=sys.stderr)
        return 1

    if args.list_users:
        for name in list_user_names(plex):
            print(name)
        return 0

    if not args.user:
        print("error: --user is required (or use --list-users)", file=sys.stderr)
        return 1
    if not args.maps:
        print("error: at least one --map SRC:DST is required", file=sys.stderr)
        return 1
    if not args.root:
        print("error: at least one --root PATH is required", file=sys.stderr)
        return 1

    roots: list[Path] = []
    for r in args.root:
        root = Path(r).expanduser().resolve()
        if not root.is_dir():
            print(f"error: --root does not exist or is not a directory: {r}", file=sys.stderr)
            return 1
        roots.append(root)

    print("Skipping user switch for now")
    user_plex = plex
    # username = resolve_user(plex, args.user)
    # try:
    #     user_plex = plex.switchUser(username)
    # except Exception as e:
    #     print(f"error: cannot switch to user {username!r}: {e}", file=sys.stderr)
    #     return 1

    cands = collect_candidates(user_plex, args.maps, roots, section_types(args))
    do_delete = bool(args.delete)
    print_report(cands, dry_run=not do_delete)

    if not do_delete:
        return 0

    if not cands:
        return 0

    if not args.yes:
        confirm = input('Type DELETE to permanently remove these files: ')
        if confirm != "DELETE":
            print("aborted")
            return 1

    deleted, freed = delete_candidates(cands)
    if deleted:
        titles = {c.section_title for c in cands}
        try:
            refresh_after_delete(plex, titles)
        except Exception as e:
            print(f"warning: trash/refresh failed: {e}", file=sys.stderr)
    print(f"\ndeleted {deleted} file(s), freed {format_size(freed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
