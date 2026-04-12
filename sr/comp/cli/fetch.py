"""
Fetch the deployed revisions of the compstate from all known hosts.

This will fetch revisions of the compstate from its 'origin' git remote and from
its various deployments.
"""

from __future__ import annotations

import argparse
import sys


def command(args: argparse.Namespace) -> None:
    from sr.comp.cli.deploy import (
        get_current_state,
        get_deployments,
        ref_compstate,
        UnableToGetStateError,
    )
    from sr.comp.cli.interaction_utils import BOLD, CLIInteractions, ENDC, FAIL
    from sr.comp.raw_compstate import RawCompstate

    compstate = RawCompstate(args.compstate, local_only=False)
    interactions = CLIInteractions()
    hosts = get_deployments(compstate, interactions)

    print("Fetching upstream... ", end="")
    sys.stdout.flush()
    compstate.fetch()
    print("done.")

    for host in hosts:
        print(f"Fetching {host}... {BOLD}{FAIL}", end="")
        sys.stdout.flush()

        try:
            state = get_current_state(host, interactions)
        except UnableToGetStateError:
            continue
        finally:
            print(ENDC, end='')
            sys.stdout.flush()

        compstate.fetch(ref_compstate(host), [state], quiet=True)
        print(f"{state} fetched.")


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg, *_ = __doc__.strip().splitlines()
    parser = subparsers.add_parser(
        'fetch',
        help=help_msg,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('compstate', help="competition state repository")
    parser.set_defaults(func=command)
