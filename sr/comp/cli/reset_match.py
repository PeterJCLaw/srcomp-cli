"""
Reset the compstate back to before the start of the given match.

This is achieved by inserting a delay so that the given match is in the future.
The point in time before the match is either:
 * the "release threshold" if the compstate has opted-in to match releasing, or
 * the start of the slot

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


def reset_match(compstate_path: Path, match_number: MatchNumber | None) -> MatchNumber:
    from sr.comp.cli import yaml_round_trip as yaml
    from sr.comp.comp import SRComp

    compstate = SRComp(compstate_path)
    if match_number is None:
        now = compstate.schedule.datetime_now
        current_matches = compstate.operations.get_matches_at(now).matches
        if not current_matches:
            raise Exception("Not currently in a match, specify a valid match number instead")
        match_number = min(x.num for x in current_matches)

    def get_match(num: MatchNumber) -> Match:
        return first(compstate.schedule.matches[num].values())

    current_match: Match = get_match(match_number)

    delay_target = current_match.start_time

    operations_path = compstate_path / 'operations.yaml'
    if operations_path.exists():
        # If the release threshold is explicitly set, use that rather than the
        # slot start time as our delay target.
        delay_target = compstate.operations.get_arena_times(current_match).release_threshold

        with yaml.edit(operations_path) as operations_yaml:
            operations: OperationsData = operations_yaml['operations']

            previous_match_number = MatchNumber(match_number - 1)
            if previous_match_number < 0:
                operations['released_match'] = None
            else:
                previous_match = get_match(previous_match_number)
                operations['released_match'] = {
                    'number': previous_match_number,
                    'time': compstate.operations.get_arena_times(previous_match).release_threshold,  # noqa: E501
                }

    # Add delay
    how_long = compstate.schedule.datetime_now - delay_target
    how_long_seconds = int(how_long.total_seconds())

    with yaml.edit(compstate_path / 'schedule.yaml') as schedule:
        add_delay.add_delay(schedule, how_long_seconds, current_match.start_time)

    return match_number


def command(args: argparse.Namespace) -> None:
    from sr.comp.raw_compstate import RawCompstate

    compstate = RawCompstate(args.compstate, local_only=False)

    deploy.require_no_changes(compstate)

    if not args.no_pull:
        with deploy.exit_on_exception():
            compstate.pull_fast_forward()

    match_number = reset_match(args.compstate, args.match_number)

    deploy.require_valid(compstate)

    with deploy.exit_on_exception(kind=RuntimeError):
        compstate.stage('schedule.yaml')
        compstate.stage('operations.yaml')
        msg = f"Reset match {match_number}"
        compstate.commit(msg)

    if args.deploy:
        hosts = deploy.get_deployments(compstate)
        deploy.run_deployments(args, compstate, hosts)


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg, *_ = __doc__.strip().splitlines()
    parser = subparsers.add_parser(
        'reset-match',
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
