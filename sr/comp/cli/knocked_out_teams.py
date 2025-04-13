from __future__ import annotations

import argparse
import collections
import dataclasses
import itertools
from pathlib import Path
from typing import Iterable, Iterator

from sr.comp.comp import SRComp
from sr.comp.match_period import Match
from sr.comp.types import MatchNumber, TLA


@dataclasses.dataclass(frozen=True)
class Round:
    number: int
    name: str
    teams_this_round: frozenset[TLA]

    teams_remaining: frozenset[TLA]
    """
    Teams known to be in this or future rounds.

    This is needed to cope with knockout structures where some seeds bypass
    early rounds.
    """

    teams_out: frozenset[TLA]
    """
    Teams knocked out by the prior round's matches.

    This will include teams whose matches in the prior round have not been
    scored. Callers should check `prior_rounds_complete` to understand the state
    of the scoring.
    """

    prior_rounds_complete: bool
    """
    Whether the scoring for all the matches prior to ths round has completed and
    thus the knockouts for this round are completely known.
    """

    this_round_complete: bool
    """
    Whether the scoring for all the matches up to and including ths round have
    completed and thus the knockouts for this round are completely known.
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
    def teams_from_matches(matches: Iterable[Match]) -> frozenset[TLA]:
        teams = set(itertools.chain.from_iterable(x.teams for x in matches))
        return frozenset(x for x in teams if x is not None)

    rounds = comp.schedule.knockout_rounds

    # Teams at the end of the league. Note that this doesn't include teams which
    # have dropped out of their own accord by that point.
    first_knockouts_match = MatchNumber(comp.schedule.n_league_matches)
    teams_last_round: frozenset[TLA]
    teams_last_round = frozenset(
        tla
        for tla, team in comp.teams.items()
        if team.is_still_around(first_knockouts_match)
    )

    teams_with_future_matches = teams_from_matches(
        itertools.chain.from_iterable(
            (
                x.values()
                for x in comp.schedule.matches[comp.scores.last_scored_match + 1:]
            ),
        ),
    )

    all_teams_out = comp.teams.keys() - teams_with_future_matches

    last_round_by_team = {}

    for tla in all_teams_out:
        for i, matches in enumerate(rounds):
            teams_this_round = teams_from_matches(matches)
            for tla in teams_this_round & all_teams_out:
                last_round_by_team[tla] = i

    out_by_round = collections.defaultdict(set)
    for tla, round_ in last_round_by_team.items():
        out_by_round[round_].add(tla)

    last_round_num = len(rounds) - 1
    for i, matches in enumerate(rounds):
        teams_this_round = teams_from_matches(matches)
        teams_out = frozenset(out_by_round.get(i, ()))
        yield Round(
            i,
            round_name(last_round_num - i),
            teams_this_round=teams_this_round,
            teams_remaining=frozenset(),
            teams_out=teams_out,
            prior_rounds_complete=True,
            this_round_complete=comp.scores.last_scored_match >= max(x.num for x in matches),
        )


def command(settings: argparse.Namespace) -> None:
    comp = SRComp(settings.compstate)

    for round_info in teams_and_rounds(comp):
        print(f"## Teams not in round {round_info.number} ({round_info.name})")
        print("Fully scored" if round_info.this_round_complete else "\nWARNING: Not fully scored")
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
                break

        for tla in sorted(round_info.teams_out):
            print(tla, comp.teams[tla].name)

        print()

    print(f"Last scored match: {comp.scores.last_scored_match}")


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
