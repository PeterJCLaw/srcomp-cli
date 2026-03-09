from __future__ import annotations

import argparse
import collections
import dataclasses
import itertools
from collections.abc import (
    Callable,
    Collection,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from pathlib import Path
from typing import Protocol

from sr.comp.comp import SRComp
from sr.comp.knockout_scheduler import UNKNOWABLE_TEAM
from sr.comp.match_period import Match
from sr.comp.teams import Team
from sr.comp.types import MatchId, MatchNumber, TLA


class MinimalSchedule(Protocol):
    @property
    def knockout_rounds(self) -> Sequence[Sequence[Match]]:
        ...

    @property
    def n_league_matches(self) -> int:
        ...


@dataclasses.dataclass(frozen=True)
class RoundResults:
    number: int
    name: str

    teams_dropped_out: frozenset[TLA]
    """
    Teams who dropped out during this round's matches.

    This accounts for teams which dropped out of their own accord, rather than
    because they were knocked out.
    """

    teams_knocked_out: frozenset[TLA]
    """
    Teams knocked out during this round's matches.

    This includes only teams which are confirmed to be knocked out due to their
    matches having all been scored.
    """

    prior_rounds_complete: bool
    """
    Whether the scoring for all the matches prior to ths round has completed and
    thus the knockouts for this round are completely known.
    """


@dataclasses.dataclass(frozen=True)
class TeamInfo:
    tla: TLA
    matches: Collection[Match]
    last_appearance: int
    all_matches_scored: bool


def round_name(round_number: int, *, final_round_number: int) -> str:
    rounds_left = final_round_number - round_number
    if rounds_left == 0:
        return "Finals"
    elif rounds_left == 1:
        return "Semi Finals"
    elif rounds_left == 2:
        return "Quarter Finals"
    return f"Round {round_number}"


def teams_and_rounds(
    teams: Mapping[TLA, Team],
    schedule: MinimalSchedule,
    has_scores: Callable[[Match], bool],
) -> Iterator[RoundResults]:
    """
    Compute which teams were knockout out in which rounds.
    """

    # This must not rely too much on the structure of the actual knockout. In
    # particular we cannot assume that winning teams will appear in every round
    # -- since that constrains the nature of the knockout.
    #
    # Instead we rely on the following properties:
    #  * Teams who have un-scored matches have not yet been knocked out
    #  * Teams with fully scored matches and no future appearances must have
    #    been knocked out
    #  * Teams which have been knocked out can be considered as "knocked out" in
    #    the round during which they had their last appearance
    #
    # Teams which drop out of their own accord are identified and excluded from
    # consideration for being "knocked out".

    def get_match_id(match: Match) -> MatchId:
        return match.arena, match.num

    def teams_from_matches(matches: Iterable[Match]) -> frozenset[TLA]:
        teams = set(itertools.chain.from_iterable(x.teams for x in matches))
        return frozenset(x for x in teams if x is not None)

    rounds = schedule.knockout_rounds
    knockout_matches = [m for r in rounds for m in r]

    round_nums_by_match: dict[MatchId, int] = {}
    for i, matches in enumerate(rounds):
        for match in matches:
            round_nums_by_match[get_match_id(match)] = i

    matches_by_team: collections.defaultdict[TLA, list[Match]]
    matches_by_team = collections.defaultdict(list)
    for match in knockout_matches:
        for tla in match.teams:
            if tla is None or tla == UNKNOWABLE_TEAM:
                continue
            matches_by_team[tla].append(match)

    team_infos: dict[TLA, TeamInfo] = {}
    for tla, matches in matches_by_team.items():
        team_infos[tla] = TeamInfo(
            tla,
            matches,
            last_appearance=round_nums_by_match[get_match_id(matches[-1])],
            all_matches_scored=all(has_scores(m) for m in matches),
        )

    teams_by_last_appearance: collections.defaultdict[int, list[TeamInfo]]
    teams_by_last_appearance = collections.defaultdict(list)
    for team_info in team_infos.values():
        teams_by_last_appearance[team_info.last_appearance].append(team_info)

    final_round_num = len(rounds) - 1

    # Teams which don't enter the knockouts

    # Teams at the end of the league. Note that this doesn't include teams which
    # have dropped out of their own accord by that point.
    first_knockouts_match = MatchNumber(schedule.n_league_matches)
    teams_after_league: collections.defaultdict[bool, list[TLA]]
    teams_after_league = collections.defaultdict(list)
    for tla, team in teams.items():
        teams_after_league[team.is_still_around(first_knockouts_match)].append(tla)

    yield RoundResults(
        number=-1,
        name="League",
        teams_dropped_out=frozenset(teams_after_league[False]),
        teams_knocked_out=frozenset(teams_after_league[True] - team_infos.keys()),
        prior_rounds_complete=bool(team_infos),
    )

    final_round_num = len(rounds) - 1

    # Results for the knockout rounds themselves
    for i, matches in enumerate(rounds):
        teams_this_round = teams_from_matches(matches)

        teams_dropped_out = frozenset(
            tla
            for tla, team in teams.items()
            if team.is_still_around(matches[0].num)
            if not team.is_still_around(matches[-1].num)
        )

        teams_knocked_out = frozenset(
            x.tla
            for x in teams_by_last_appearance[i]
            if x.tla not in teams_dropped_out
            if x.all_matches_scored
        )

        yield RoundResults(
            i,
            round_name(i, final_round_number=final_round_num),
            teams_dropped_out=teams_dropped_out,
            teams_knocked_out=teams_knocked_out,
            prior_rounds_complete=UNKNOWABLE_TEAM not in teams_this_round,
        )


def command(settings: argparse.Namespace) -> None:
    comp = SRComp(settings.compstate)

    def has_scores(match: Match) -> bool:
        return comp.scores.get_scores(match) is not None

    def print_teams(teams: Iterable[TLA]) -> None:
        for tla in sorted(teams):
            print(tla, comp.teams[tla].name)

    results = list(teams_and_rounds(comp.teams, comp.schedule, has_scores))

    # Show all but the final (which has no real meaning).
    # TODO: handle there being a tiebreaker.
    for round_info in results[:-1]:
        print(f"## Teams not longer present after {round_info.name}")
        print()
        if round_info.teams_dropped_out:
            print("-- Teams dropping out (of their own accord)")
            print_teams(round_info.teams_dropped_out)
            print()

        if not round_info.prior_rounds_complete:
            if settings.force:
                print("Warning: ", end='')

            print(
                "This round is not yet fully scored, knocked-out teams this "
                "round are not yet confirmed.",
            )
            print()

            if not settings.force:
                return

        if round_info.teams_dropped_out:
            print("-- Teams knocked out")
            print()

        print_teams(round_info.teams_knocked_out)

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
