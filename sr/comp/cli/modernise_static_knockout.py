"""
Update the static knockout schedule configuration format.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def command(settings: argparse.Namespace) -> None:
    from sr.comp.cli import yaml_round_trip as yaml
    from sr.comp.knockout_scheduler import StaticScheduler

    with yaml.edit(settings.compstate / 'schedule.yaml') as schedule:
        static_knockout = schedule.get('static_knockout')
        if static_knockout is None:
            print("Warning: Schedule does not have a static configuration")
            return

        # Update in-place to preserve comments as much as we can
        new_config = StaticScheduler.modernise_config_if_needed(static_knockout)

        if new_config == static_knockout:
            print("Static knockout config already up to date, nothing to do")
            return

        static_knockout.clear()
        static_knockout.update(new_config)


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        'modernise-static-knockout',
        help=__doc__.strip().splitlines()[0],
        description=__doc__,
    )
    parser.add_argument(
        'compstate',
        help="competition state repository",
        type=Path,
    )
    parser.set_defaults(func=command)
