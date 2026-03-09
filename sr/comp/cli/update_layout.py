"""
Update the layout based on a list of teams.

The user is responsible for ensuring that the ordering and groupings are
correct in the layout _before_ running this. Groups of teams in the
original are simply replaced with equivalently sized groups.
Any excess teams in the list are added to the final group.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Generic, Sequence, TypeVar

T = TypeVar('T')


class Takeable(Generic[T]):
    def __init__(self, source: Sequence[T]) -> None:
        self._source = source
        self._idx = 0

    @property
    def has_more(self) -> bool:
        return self._idx < len(self._source)

    @property
    def remainder(self) -> Sequence[T]:
        return self._source[self._idx:]

    def take(self, n: int) -> Sequence[T]:
        start = self._idx
        self._idx = end = start + n
        return self._source[start:end]


def command(settings: argparse.Namespace) -> None:
    from sr.comp.cli import yaml_round_trip as yaml

    with yaml.edit(settings.compstate / 'layout.yaml') as layout:
        layout_teams = layout['teams']

        with open(settings.teams_list) as tlf:
            teams_list = []
            for line in tlf.readlines():
                tla = line.split('#', 1)[0].strip()
                if tla:
                    teams_list.append(tla)

        teams = Takeable(teams_list)

        for place in layout_teams:
            # Ensure we replace the content of the list, but not the list
            # itself so that the file's own layout is preserved
            loc_teams = place['teams']
            loc_teams[:] = teams.take(len(loc_teams))

        if teams.has_more:
            layout_teams[-1]['teams'] += teams.remainder

    print("Layout updated. You should consider re-importing the schedule now.")


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        'update-layout',
        help=__doc__.strip().splitlines()[0],
        description=__doc__,
    )
    parser.add_argument(
        'compstate',
        help="competition state repository",
        type=Path,
    )
    parser.add_argument(
        'teams_list',
        help="file containing the list of teams",
        type=Path,
    )
    parser.set_defaults(func=command)
