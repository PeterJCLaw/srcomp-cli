"""
Release a given match in preparation for running it.

Commutates can opt-in to "match releasing" by having an `operations.yaml` file
which contains configuration for the release timings. This command edits that
file to mark the given match as having been released.

This is useful during match operations in the event a match needs to be
abandoned and re-run.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar

from sr.comp.cli import add_delay, deploy
from sr.comp.match_period import Match
from sr.comp.types import MatchNumber, OperationsData

T = TypeVar('T')


def first(iterable: Iterable[T]) -> T:
    return next(i for i in iterable)


def release_match(compstate_path: Path, match_number: MatchNumber | None) -> MatchNumber:
    from sr.comp.cli import yaml_round_trip as yaml
    from sr.comp.comp import SRComp
    from sr.comp.match_operations import MatchState

    operations_path = compstate_path / 'operations.yaml'
    if not operations_path.exists():
        raise Exception("Cannot release matches in a compstate without an 'operations.yaml'")

    compstate = SRComp(compstate_path)
    now = compstate.schedule.datetime_now
    if match_number is None:
        current_matches = compstate.operations.get_matches_at(now).matches
        if not current_matches:
            raise Exception("Not currently in a match, specify a valid match number instead")
        match_number = min(x.num for x in current_matches)

    match: Match = first(compstate.schedule.matches[match_number].values())
    state = compstate.operations.get_match_state(match, now)
    if state == MatchState.RELEASED:
        print(f"Match {match_number} already released")
        exit(1)

    with yaml.edit(operations_path) as operations_yaml:
        when = compstate.schedule.datetime_now.replace(microsecond=0)

        operations: OperationsData = operations_yaml['operations']
        operations['released_match'] = {
            'number': match_number,
            'time': when,
        }

    # Add delay if needed
    times = compstate.operations.get_arena_times(match)
    if when > times.release_threshold:
        how_long = when - times.release_threshold
        how_long_seconds = int(how_long.total_seconds())
        print(
            f"Match {match.num} originally scheduled at {times.start} will "
            f"be scheduled at {times.start + how_long}.",
        )

        with yaml.edit(compstate_path / 'schedule.yaml') as schedule:
            add_delay.add_delay(schedule, how_long_seconds, match.start_time)

        # Self check
        new_state = SRComp(compstate_path)
        new_match: Match = first(new_state.schedule.matches[match_number].values())
        new_times = new_state.operations.get_arena_times(new_match)
        assert new_times.release_threshold == when, (new_times.release_threshold, when)

    return match_number


def command(args: argparse.Namespace) -> None:
    from sr.comp.raw_compstate import RawCompstate

    compstate = RawCompstate(args.compstate, local_only=False)

    deploy.require_no_changes(compstate)

    if not args.no_pull:
        with deploy.exit_on_exception():
            compstate.pull_fast_forward()

    match_number = release_match(args.compstate, args.match_number)

    deploy.require_valid(compstate)

    with deploy.exit_on_exception(kind=RuntimeError):
        compstate.stage('schedule.yaml')
        compstate.stage('operations.yaml')
        msg = f"Release match {match_number}"
        compstate.commit(msg)

    if args.deploy:
        hosts = deploy.get_deployments(compstate)
        deploy.run_deployments(args, compstate, hosts)


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg, *_ = __doc__.strip().splitlines()
    parser = subparsers.add_parser(
        'release-match',
        help=help_msg,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--no-deploy',
        dest='deploy',
        action='store_false',
        default=True,
        help="Disable deploying the compstate after making the edit",
    )
    parser.add_argument(
        '--no-pull',
        action='store_true',
        help="Skip updating to the latest revision",
    )
    deploy.add_options(parser)
    parser.add_argument(
        'compstate',
        type=Path,
        help="competition state repository",
    )
    parser.add_argument(
        '--match-number',
        type=int,
        default=None,
        help=(
            "A specific match number to release. "
            "Note that releasing a match implicitly includes all previous matches. "
            "Defaults to the current match."
        ),
    )
    parser.set_defaults(func=command)
