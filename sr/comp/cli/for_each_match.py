"""
Run a command for each of the given matches.

The matches can be specified as a comma-separated list and/or dash-separated
ranges. The commands will be run in the numeric order of matches (rather than
the given order) and only once per match.

Where a compstate has multiple arenas the command will be run for each arena, in
the order the arenas are defined within the compstate. Alternatively a specific
arena can be specified to limit the commands to matches in that arena.

A number of placeholders are available for use in your command, so you can
control how information about each match is passed to the command. The TLAS
placeholder will always include enough entries for every zone in the arena,
using '-' to represent an empty zone.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable, TYPE_CHECKING

from sr.comp.cli.interaction_utils import CLIInteractions

if TYPE_CHECKING:
    from sr.comp.match_period import Match


def get_tlas(match: Match) -> list[str]:
    return [
        x if x is not None else '-'
        for x in match.teams
    ]


PLACEHOLDERS: dict[str, Callable[[Match], list[str]]] = {
    'ARENA': lambda x: [x.arena],
    'NUMBER': lambda x: [str(x.num)],
    'TLAS': get_tlas,
    'TYPE': lambda x: [str(x.type.value)],
}


class PlaceholderExpander:
    def __init__(self, match: Match) -> None:
        self.match = match

    @staticmethod
    def validate(value: str) -> None:
        if value.startswith('@') and value[1:] not in PLACEHOLDERS:
            print(f"Warning: unrecognised value {value!r}.", file=sys.stderr)

    def __getitem__(self, key: str) -> str:
        return ' '.join(PLACEHOLDERS[key](self.match))

    def expand(self, value: str) -> list[str]:
        if value.startswith('@'):
            key = value[1:]
            fn = PLACEHOLDERS.get(key)
            if fn:
                return fn(self.match)

        return [value.format_map(self)]


def replace_placeholders(match: Match, command: list[str]) -> list[str]:
    import itertools

    expander = PlaceholderExpander(match)
    return list(itertools.chain.from_iterable(
        expander.expand(x)
        for x in command
    ))


def command(args: argparse.Namespace) -> None:
    import subprocess

    from sr.comp.comp import SRComp

    compstate = SRComp(args.compstate)
    interactions = CLIInteractions()

    if args.arena:
        if args.arena not in compstate.arenas:
            print("{} is not a valid arena, choose from {}".format(
                args.arena,
                ", ".join(compstate.arenas.keys()),
            ))

    for part in args.command:
        PlaceholderExpander.validate(part)

    try:
        for match_number in sorted(args.matches):
            for arena, match in compstate.schedule.matches[match_number].items():
                if args.arena not in (arena, None):
                    continue

                command = replace_placeholders(match, args.command)
                subprocess.check_call(command)

    except subprocess.CalledProcessError as e:
        interactions.show_error(str(e))
        exit(1)


def add_options(parser: argparse.ArgumentParser) -> None:
    from sr.comp.matches import parse_ranges

    parser.add_argument(
        '--arena',
        default=None,
        help=(
            "Limit to just one arena. By default the command is run for each "
            "arena in turn."
        ),
    )
    parser.add_argument(
        'matches',
        type=parse_ranges,
        help="List of matches or match ranges, for example '1,3-5'.",
    )
    parser.add_argument(
        'command',
        nargs='+',
        help=(
            "Command to run. Supports the following placeholders: {}. "
            "Placeholders spelled like {{THIS}} will be replaced as strings "
            "anywhere within the command arguments. Placeholders which are an "
            "argument on their own and spelled exactly as @THIS will expand to "
            "one or more replacement arguments when the command is run.".format(
                ", ".join(PLACEHOLDERS.keys()),
            )
        ),
    )


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        'for-each-match',
        help="Run a command for each of the given matches.",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('compstate', help="competition state repository")
    add_options(parser)
    parser.set_defaults(func=command)
