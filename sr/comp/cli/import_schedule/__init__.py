"""
Import a league.yaml from a schedule file.

A schedule file specifies matches one-per-line, as follows:

A 'match' consists of a number of unique identifiers separated by pipe
characters. Identifiers are arbitrary strings, though a common pattern
from schedule-generating tooling is to use integers.

The total number of identifiers in the file should be equal to or greater
than the number of teams in the compstate. In the latter case, `--ignore-ids`
can optionally be used to indicate explicitly which to ignore. This can be
useful when the number of teams does not evenly divide into the number of
entrants in match.

The number of identifiers in a given match must be a multiple of the
number of teams per game (currently 4), up to the number of arenas in
the compstate.

Whitespace (other than newlines) within the file is ignored, as is any
content to the right of a hash character (#), including the hash. As a
result hash characters may be used to start line comments.

Example schedules for 48, 52 or 56 teams are available  at:
https://github.com/PeterJCLaw/srobo-schedules/tree/master/seed_schedules

Teams which are marked as having dropped out before the first match being
scheduled will not be considered for inclusion in the schedule.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from sr.comp.cli.import_schedule import loading, teams_mapping
from sr.comp.cli.import_schedule.types import Configuration, RawMatch
from sr.comp.types import MatchNumber


def get_first_match_number(existing_match_numbers: Iterable[MatchNumber]) -> MatchNumber:
    if not existing_match_numbers:
        return MatchNumber(0)

    return MatchNumber(max(existing_match_numbers) + 1)


def get_configuration(
    compensate_path: Path,
    team_order_strategy: teams_mapping.Strategy,
    existing_match_numbers: Iterable[MatchNumber],
) -> Configuration:
    first_match_number = get_first_match_number(existing_match_numbers)

    # Grab the teams and arenas
    try:
        team_ids, arena_ids, teams_per_game = loading.load_teams_areans(
            compensate_path,
            first_match_number,
        )
    except Exception as e:
        print(f"Failed to load existing state ({e}).")
        print("Make it valid (consider removing the league.yaml and layout.yaml)")
        print("and try again.")
        exit(1)

    # Semi-randomise
    team_ids = teams_mapping.order_teams(
        compensate_path,
        team_ids,
        team_order_strategy,
    )

    return Configuration(arena_ids, team_ids, teams_per_game, first_match_number)


def command(args: argparse.Namespace) -> None:
    from sr.comp.cli.import_schedule import core

    with open(args.schedule) as sfp:
        schedule_lines = loading.tidy(sfp.readlines())

    league_yaml = loading.league_yaml_path(args.compstate)
    matches: dict[MatchNumber, RawMatch] = {}
    if args.extend:
        matches = loading.load_league_yaml(league_yaml)

    config = get_configuration(
        args.compstate,
        args.team_order_strategy,
        matches.keys(),
    )

    new_matches, bad_matches = core.build_schedule(
        config,
        schedule_lines,
        args.ignore_ids,
    )

    # Print any warnings about the matches
    for bad_match in bad_matches:
        print(
            f"Warning: match {bad_match.arena}:{bad_match.num} only has "
            f"{bad_match.num_teams} teams.",
        )

    # Note: make sure to update in-place and then save back using the same
    # mapping as was loaded to preserve any comments in the YAML.
    matches.update(new_matches)

    # Save the matches to the file
    loading.dump_league_yaml(matches, league_yaml)


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        'import-schedule',
        help="Import a league.yaml file from a schedule file.",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Changing this? Also update the reference to this argument in
    # `build_schedule` in core.py and in the docstring for this module.
    parser.add_argument(
        '-i',
        '--ignore-ids',
        type=loading.parse_ids,
        help=(
            "Comma separated list of ids (as present in the schedule file) to ignore. "
            "Where this is not provided and the number of ids is greater than "
            "the number of teams, heuristics will be used to determine which ids "
            "are assigned teams."
        ),
    )
    parser.add_argument(
        '--extend',
        default=False,
        action='store_true',
        help=(
            "Whether to replace (the default) or extend the existing league "
            "with the matches in the given schedule file."
        ),
    )
    parser.add_argument(
        '--team-order-strategy',
        choices=teams_mapping.Strategy,
        default=teams_mapping.Strategy.AUTO,
        type=teams_mapping.Strategy,
        help="How to map schedule ids to TLAs",
    )
    parser.add_argument('compstate', type=Path, help="competition state repository")
    parser.add_argument('schedule', type=Path, help="schedule to import")
    parser.set_defaults(func=command)
