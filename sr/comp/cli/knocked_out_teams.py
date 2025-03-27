from __future__ import annotations

import argparse
import dataclasses
import itertools
from pathlib import Path
from typing import Iterable, Iterator

from sr.comp.comp import SRComp
from sr.comp.knockout_scheduler import UNKNOWABLE_TEAM
from sr.comp.match_period import Match
from sr.comp.types import TLA


@dataclasses.dataclass(frozen=True)
class Round:
    number: int
    name: str
    teams_this_round: frozenset[TLA | None]

    teams_remaining: frozenset[TLA]
    """
    Teams known to be in this or future rounds.

    This is needed to cope with knockout structures where some seeds bypass
    early rounds.
    """

    prior_rounds_complete: bool
    """
    Whether the scoring for all the matches prior to ths round has completed and
    thus the knockouts for this round are completely known.
    """


def round_name(rounds_left: int) -> str:
    if rounds_left == 0:
        return "Finals"
    elif rounds_left == 1:
        return "Semi Finals"
    elif rounds_left == 2:
        return "Quarter Finals"
    return ""


def teams_and_rounds(comp: SRComp) -> Iterator[Round]:
    def teams_from_matches(matches: Iterable[Match]) -> set[TLA | None]:
        return set(itertools.chain.from_iterable(x.teams for x in matches))

    rounds = comp.schedule.knockout_rounds

    last_round_num = len(rounds) - 1
    for i, matches in enumerate(rounds):
        teams_this_round = teams_from_matches(matches)
        teams_remaining = teams_from_matches(itertools.chain(*rounds[i:]))

        yield Round(
            i,
            round_name(last_round_num - i),
            frozenset(teams_this_round),
            frozenset(x for x in teams_remaining if x is not None),
            prior_rounds_complete=UNKNOWABLE_TEAM not in teams_this_round,
        )


def command(settings: argparse.Namespace) -> None:
    comp = SRComp(settings.compstate)

    teams_last_round: frozenset[TLA | None] = frozenset()
    for round_info in teams_and_rounds(comp):
        print(f"## Teams not in round {round_info.number} ({round_info.name})")
        print()

        if not round_info.prior_rounds_complete:
            if settings.force:
                print("Warning: ", end='')

            print(
                "Prior rounds are not yet fully scored, knocked-out teams this "
                "round are not yet confirmed.",
            )
            print()

            if not settings.force:
                return

        out = teams_last_round - round_info.teams_remaining
        teams_out = [t for t in out if t is not None]
        for tla in sorted(teams_out):
            print(tla, comp.teams[tla].name)

        teams_last_round = round_info.teams_this_round
        print()


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg = "Show the teams knocked out of each knockout round."
    parser = subparsers.add_parser(
        'knocked-out-teams',
        help=help_msg,
        description=help_msg,
    )
    parser.add_argument(
        'compstate',
        help="competition state repository",
        type=Path,
    )
    parser.add_argument(
        '--force',
        help="Show knockouts even for incompletely scored rounds.",
        action='store_true',
        default=False,
    )
    parser.set_defaults(func=command)
