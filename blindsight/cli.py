"""Command-line interface for Blindsight."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .extractor import extract
from .modules import REGISTRY, load_registry

_ALL_MODULES = [m.NAME for m in REGISTRY]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="blindsight",
        description="Turn an image into a structured text descriptor for LLMs.",
    )
    parser.add_argument("image", help="path to the input image")
    parser.add_argument("-o", "--output",
                        help="write the descriptor to this file instead of stdout")
    parser.add_argument("-f", "--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("-m", "--modules",
                        help=f"comma-separated subset to run. built-in choices: {','.join(_ALL_MODULES)} "
                             "(add --enable-plugins for third-party modules)")
    parser.add_argument("--enable-plugins", action="store_true",
                        help="also discover and run third-party modules registered "
                             "under the 'blindsight.modules' entry-point group")
    parser.add_argument("--version", action="version",
                        version=f"blindsight {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    registry = load_registry(enable_plugins=args.enable_plugins)
    available = [m.NAME for m in registry]

    modules = None
    if args.modules:
        modules = [m.strip() for m in args.modules.split(",") if m.strip()]
        unknown = [m for m in modules if m not in available]
        if unknown:
            print(f"error: unknown module(s): {', '.join(unknown)}", file=sys.stderr)
            print(f"available: {', '.join(available)}", file=sys.stderr)
            return 2

    try:
        descriptor = extract(args.image, modules=modules,
                             enable_plugins=args.enable_plugins)
    except FileNotFoundError:
        print(f"error: image not found: {args.image}", file=sys.stderr)
        return 1
    except Exception as exc:  # surface load/decoding errors cleanly
        print(f"error: could not process image: {exc}", file=sys.stderr)
        return 1

    rendered = (json.dumps(descriptor.to_json(), indent=2)
                if args.format == "json" else descriptor.to_text())

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(rendered + "\n")
        print(f"wrote {args.format} descriptor to {args.output}", file=sys.stderr)
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
