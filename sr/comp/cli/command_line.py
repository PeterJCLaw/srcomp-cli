"""srcomp command-line interface."""

from __future__ import annotations

import argparse
import sys

from . import (
    add_delay,
    awards,
    delay,
    deploy,
    fetch,
    for_each_match,
    import_schedule,
    knocked_out_teams,
    list_midi_ports,
    match_order_teams,
    modernise_static_knockout,
    print_schedule,
    schedule_league,
    scorer,
    shift_matches,
    show_league_table,
    show_schedule,
    summary,
    top_match_points,
    update_layout,
    validate,
    yaml_round_trip,
    youtube_chapters,
)


def add_list_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    def command(settings: argparse.Namespace) -> None:
        commands = subparsers.choices.keys()
        print(" ".join(commands))

    help_text = "Lists the available commands; useful for adding " \
                "auto-completion of command names."

    parser = subparsers.add_parser('list-commands', help=help_text, description=help_text)
    parser.set_defaults(func=command)


def argument_parser() -> argparse.ArgumentParser:
    """A parser for CLI tool command line arguments, from argparse."""
    parser = argparse.ArgumentParser(description="srcomp command-line interface")
    subparsers = parser.add_subparsers(title="commands")
    add_list_commands(subparsers)

    add_delay.add_subparser(subparsers)
    awards.add_subparser(subparsers)
    delay.add_subparser(subparsers)
    deploy.add_subparser(subparsers)
    fetch.add_subparser(subparsers)
    for_each_match.add_subparser(subparsers)
    import_schedule.add_subparser(subparsers)
    knocked_out_teams.add_subparser(subparsers)
    list_midi_ports.add_subparser(subparsers)
    match_order_teams.add_subparser(subparsers)
    modernise_static_knockout.add_subparser(subparsers)
    print_schedule.add_subparser(subparsers)
    schedule_league.add_subparser(subparsers)
    scorer.add_subparser(subparsers)
    shift_matches.add_subparser(subparsers)
    show_league_table.add_subparser(subparsers)
    show_schedule.add_subparser(subparsers)
    summary.add_subparser(subparsers)
    top_match_points.add_subparser(subparsers)
    update_layout.add_subparser(subparsers)
    validate.add_subparser(subparsers)
    yaml_round_trip.add_subparser(subparsers)
    youtube_chapters.add_subparser(subparsers)

    return parser


def main(args: list[str] | None = None) -> None:
    """Run as the CLI tool."""
    if args is None:
        args = sys.argv[1:]
    parser = argument_parser()
    settings = parser.parse_args(args)
    if 'func' in settings:
        settings.func(settings)
    else:
        parser.print_help()
