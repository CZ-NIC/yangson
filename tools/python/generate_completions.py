"""Generate shell completions with ``uv run generate_completions.py``."""

import argparse
from pathlib import Path

import shtab

from yangson.cli import get_parser


def add_completions(parser: argparse.ArgumentParser) -> None:
    """Annotate file arguments, including those in subcommand parsers."""
    for action in parser._actions:
        if action.dest == "model":
            action.complete = shtab.glob("*.json", "*.pickle")
        elif action.dest in {"dumpfile", "instance"}:
            action.complete = shtab.FILE
        elif isinstance(action, argparse._SubParsersAction):
            for subparser in action.choices.values():
                add_completions(subparser)


def main() -> None:
    """Write completion scripts beneath the project's completions directory."""
    output_dir = Path.cwd() / "completions"
    filenames = {"bash": "yangson", "zsh": "_yangson",
                 "fish": "yangson.fish"}
    for shell, filename in filenames.items():
        parser = get_parser()
        add_completions(parser)
        script = shtab.complete(parser, shell=shell)
        destination = output_dir / shell / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(script, encoding="utf-8")


if __name__ == "__main__":
    main()
