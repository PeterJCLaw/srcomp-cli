from __future__ import annotations

import argparse
from pathlib import Path

from sr.comp.cli import add_delay, deploy
from sr.comp.cli.interaction_utils import CLIInteractions


def command(args: argparse.Namespace) -> None:
    from sr.comp.raw_compstate import RawCompstate

    compstate = RawCompstate(args.compstate, local_only=False)
    interactions = CLIInteractions()
    hosts = deploy.get_deployments(compstate, interactions)

    deploy.require_no_changes(compstate, interactions)

    if not args.no_pull:
        with interactions.make_fatal():
            compstate.pull_fast_forward()

    how_long, when = add_delay.command(args)

    if args.when != 'now':
        msg = f"Confirm adding {how_long} delay at {when}"
        if not interactions.query_bool(msg, default=True):
            print("Leaving state with local modifications")
            exit()

    deploy.require_valid(compstate, interactions)

    with interactions.make_fatal(kind=RuntimeError):
        compstate.stage('schedule.yaml')
        msg = f"Adding {args.how_long} delay at {when}"
        compstate.commit(msg)

    deploy.run_deployments(args, compstate, hosts, interactions)


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg = "Add and deploy a delay to the competition."
    parser = subparsers.add_parser('delay', help=help_msg, description=help_msg)
    parser.add_argument(
        '--no-pull',
        action='store_true',
        help="skips updating to the latest revision",
    )
    deploy.add_options(parser)
    parser.add_argument(
        'compstate',
        type=Path,
        help="competition state repository",
    )
    add_delay.add_arguments(parser)
    parser.set_defaults(func=command)
