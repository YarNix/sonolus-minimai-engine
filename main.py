"""Minimai pack tools.

    python main.py skin <name> <source>       resources/skins/<name> from a skin folder or zip file
    python main.py effect <name> <source>     resources/effects/<name> from a folder or zip file of clips
    python main.py particle <name> <source>   resources/particles/<name> from a folder or zip file of sprites
    python main.py all <name> <folder>        all three, from <folder>/skin, <folder>/effect and <folder>/particle
                                              (each a folder or a .zip); a missing one is skipped
    python main.py localization [locale ...]  list the text each locale of localization.toml lacks
    python main.py clean [folder ...]         remove the caches (the chart folders' converted audio and
                                              backgrounds) and the sprites art and font_render drew (in the
                                              folders given, or anywhere in the project); --caches or --drawn
                                              for one of them, --dry-run to list what would go

Each source may hold a ``pack.toml`` with the pack's settings (docs/packs.md). The tools need the ``tools``
extra (``uv sync --extra tools``).
"""

import argparse
from pathlib import Path

PACKS = ("skin", "effect", "particle")


def pack(kind: str, name: str, source: Path) -> Path:
    if kind == "skin":
        from minimai.tools.skin_pack import pack_skin
        return pack_skin(name, source)

    if kind == "effect":
        from minimai.tools.effect_pack import pack_effect
        return pack_effect(name, source)

    if kind == "particle":
        from minimai.tools.particle_pack import pack_particle
        return pack_particle(name, source)

    raise ValueError(f"Unsupported '{kind}' pack kind!")


def find_all_sources(folder: Path) -> dict[str, Path]:
    sources = {}
    for kind in PACKS:
        for candidate in (folder / kind, folder / f"{kind}.zip"):
            if candidate.exists():
                sources[kind] = candidate
                break
    return sources


def main():
    parser = argparse.ArgumentParser(description="Minimai pack tools")
    commands = parser.add_subparsers(dest="command", required=True)
    for kind in PACKS:
        command = commands.add_parser(kind, help=f"build {'an' if kind[0] in 'aeiou' else 'a'} {kind} pack")
        command.add_argument("name", help=f"the pack's folder name in resources/{kind}s")
        command.add_argument("source", type=Path, help="the source folder or zip file")
    every = commands.add_parser("all", help="build the skin, effect and particle packs found in a folder")
    every.add_argument("name", help="the packs' folder name in resources/skins, effects and particles")
    every.add_argument("source", type=Path, help="folder with skin, effect and particle (each a folder or a .zip)")
    clean = commands.add_parser("clean", help="remove the caches and the drawn sprites")
    clean.add_argument("folders", nargs="*", type=Path, help="where to look for drawn sprites (default: the project)")
    only = clean.add_mutually_exclusive_group()
    only.add_argument("--caches", action="store_true", help="only the converted audio and the chart backgrounds")
    only.add_argument("--drawn", action="store_true", help="only the sprites art and font_render drew")
    clean.add_argument("-n", "--dry-run", action="store_true", help="list what would be removed, remove nothing")
    localization = commands.add_parser("localization", help="list the text each locale lacks")
    localization.add_argument("locales", nargs="*", help="locale codes (default: every locale with some text)")
    args = parser.parse_args()

    if args.command == "localization":
        from minimai.localization import report

        report(args.locales)
    elif args.command == "clean":
        from minimai.tools.cleanup import clean as clean_project

        clean_project(args.folders, caches=not args.drawn, drawn=not args.caches, dry_run=args.dry_run)
    elif args.command == "all":
        sources = find_all_sources(args.source)
        if not sources:
            raise SystemExit(f"No skin, effect or particle folder or zip file in {args.source}")
        for kind, source in sources.items():
            print(f"== {kind}: {source}")
            print(f"Written to {pack(kind, args.name, source)}")
    else:
        print(f"Written to {pack(args.command, args.name, args.source)}")


if __name__ == "__main__":
    main()
