from __future__ import annotations

import dataclasses
import itertools
import unittest
from collections.abc import Collection, Mapping, Sequence

from sr.comp.cli.knocked_out_teams import teams_and_rounds
from sr.comp.knockout_scheduler import KnockoutRound, UNKNOWABLE_TEAM
from sr.comp.match_period import Match, MatchType
from sr.comp.teams import Team
from sr.comp.types import MatchNumber, TLA

from . import factories


@dataclasses.dataclass(frozen=True)
class FakeSchedule:
    knockout_rounds: Sequence[KnockoutRound]
    n_league_matches: int


class TestKnockedOutTeams(unittest.TestCase):
    maxDiff = None

    def get_team(self, tla: str, dropped_out_after: MatchNumber | None = None) -> Team:
        return Team(TLA(tla), f"Team {tla}", rookie=False, dropped_out_after=dropped_out_after)

    def get_teams(self, tlas: Collection[str]) -> Mapping[TLA, Team]:
        return {TLA(x): self.get_team(x) for x in tlas}

    def build_match_info(
        self,
        *,
        teams: Sequence[TLA | None],
        is_scored: bool,
        type_: MatchType = MatchType.knockout,
    ) -> tuple[Match, bool]:
        return (
            factories.build_match(
                num=next(self.match_counter),
                teams=teams,
                type_=MatchType.knockout,
                use_resolved_ranking=True,
            ),
            is_scored,
        )

    def assertKnockedOutTeams(
        self,
        knockout_rounds: Sequence[Sequence[tuple[Match, bool]]],
        expected_knockouts: list[frozenset[TLA]],
    ) -> None:
        is_scored_map = {
            (m.arena, m.num): is_scored
            for r in knockout_rounds
            for m, is_scored in r
        }

        result = list(teams_and_rounds(
            self.teams,
            FakeSchedule(
                knockout_rounds=[
                    KnockoutRound(f"Round {idx}", [m for m, _ in r])
                    for idx, r in enumerate(knockout_rounds)
                ],
                n_league_matches=1,
            ),
            has_scores=lambda m: is_scored_map[m.arena, m.num],
        ))

        self.assertEqual(
            expected_knockouts,
            [x.teams_knocked_out for x in result],
        )

    def setUp(self) -> None:
        super().setUp()

        self.teams = self.get_teams([
            'AAA',
            'BBB',
            'CCC',
            'DDD',
            'EEE',
            'FFF',
            'GGG',
            'HHH',
        ])
        self.tlas = sorted(self.teams.keys())

        self.n_league_matches = 2
        self.match_counter = itertools.count(self.n_league_matches)

    # In these matches we assume that teams win in alphabetical order (which is
    # also the order they're listed in `self.tlas`) -- so 'AAA' (index `0`) wins
    # over 'CCC' (index `3`).

    # Simple cases

    def test_league_not_finished(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
                [
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
            ],
            expected_knockouts=[
                frozenset(self.tlas),
                frozenset(),
                frozenset(),
            ],
        )

    def test_league_not_finished_with_dropout(self) -> None:
        team = self.get_team('CCC', dropped_out_after=MatchNumber(0))
        self.teams = {
            **self.teams,
            team.tla: team,
        }

        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
                [
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
            ],
            expected_knockouts=[
                frozenset(self.tlas) - frozenset([team.tla]),
                frozenset(),
                frozenset(),
            ],
        )

    def test_league_just_finished(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                # -- we are here --
                [
                    self.build_match_info(teams=self.tlas[:4], is_scored=False),
                    self.build_match_info(teams=self.tlas[4:], is_scored=False),
                ],
                [
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
            ],
            expected_knockouts=[
                frozenset(),
                frozenset(),
                frozenset(),
            ],
        )

    def test_league_just_finished_smaller_knockout_than_league(self) -> None:
        team = self.get_team('ZZZ')
        self.teams = {
            **self.teams,
            team.tla: team,
        }

        self.assertKnockedOutTeams(
            knockout_rounds=[
                # -- we are here --
                [
                    self.build_match_info(teams=self.tlas[:4], is_scored=False),
                    self.build_match_info(teams=self.tlas[4:], is_scored=False),
                ],
                [
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
            ],
            expected_knockouts=[
                frozenset([team.tla]),
                frozenset(),
                frozenset(),
            ],
        )

    def test_during_first_round(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    self.build_match_info(teams=self.tlas[:4], is_scored=True),
                    # -- we are here --
                    self.build_match_info(teams=self.tlas[4:], is_scored=False),
                ],
                [
                    self.build_match_info(
                        teams=self.tlas[:2] + [UNKNOWABLE_TEAM] * 2,
                        is_scored=False,
                    ),
                ],
            ],
            expected_knockouts=[
                frozenset(),
                frozenset(self.tlas[2:4]),
                frozenset(),
            ],
        )

    def test_after_first_round(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    self.build_match_info(teams=self.tlas[:4], is_scored=True),
                    self.build_match_info(teams=self.tlas[4:], is_scored=True),
                ],
                # -- we are here --
                [
                    self.build_match_info(
                        teams=self.tlas[:2] + self.tlas[4:6],
                        is_scored=False,
                    ),
                ],
            ],
            expected_knockouts=[
                frozenset(),
                frozenset(self.tlas[2:4] + self.tlas[-2:]),
                frozenset(),
            ],
        )

    def test_after_final(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    self.build_match_info(teams=self.tlas[:4], is_scored=True),
                    self.build_match_info(teams=self.tlas[4:], is_scored=True),
                ],
                [
                    self.build_match_info(
                        teams=self.tlas[:2] + self.tlas[4:6],
                        is_scored=True,
                    ),
                ],
                # -- we are here --
            ],
            expected_knockouts=[
                frozenset(),
                frozenset(self.tlas[2:4] + self.tlas[-2:]),
                # everyone is knocked out in final (but it's not shown)
                frozenset(self.tlas[:2] + self.tlas[4:6]),
            ],
        )

    # Double elimination style cases

    def test_double_elimination_before_first_round(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                # -- we are here --
                [
                    # 1. Initial round -- everyone
                    self.build_match_info(teams=self.tlas[:4], is_scored=False),
                    self.build_match_info(teams=self.tlas[4:], is_scored=False),
                ],
                [
                    # 2. Lower bracket -- losers from round 1
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
                [
                    # 3. Upper bracket -- winders from round 1
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
                [
                    # 4. Lower bracket -- winners from round 2 + losers from round 3
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
                [
                    # Final -- winners from round 3 + winners from round 4
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
            ],
            expected_knockouts=[
                frozenset(),    # before first round
                frozenset(),    # future
                frozenset(),
                frozenset(),
                frozenset(),
                frozenset(),
            ],
        )

    def test_double_elimination_after_first_match(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    # 1. Initial round -- everyone
                    self.build_match_info(teams=self.tlas[:4], is_scored=True),
                    # -- we are here --
                    self.build_match_info(teams=self.tlas[4:], is_scored=False),
                ],
                [
                    # 2. Lower bracket -- losers from round 1
                    self.build_match_info(
                        teams=self.tlas[2:4] + [UNKNOWABLE_TEAM] * 2,
                        is_scored=False,
                    ),
                ],
                [
                    # 3. Upper bracket -- winders from round 1
                    self.build_match_info(
                        teams=self.tlas[:2] + [UNKNOWABLE_TEAM] * 2,
                        is_scored=False,
                    ),
                ],
                [
                    # 4. Lower bracket -- winners from round 2 + losers from round 3
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
                [
                    # Final -- winners from round 3 + winners from round 4
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
            ],
            expected_knockouts=[
                frozenset(),    # before first round
                frozenset(),    # partial future
                frozenset(),
                frozenset(),
                frozenset(),
                frozenset(),
            ],
        )

    def test_double_elimination_after_first_round(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    # 1. Initial round -- everyone
                    self.build_match_info(teams=self.tlas[:4], is_scored=True),
                    self.build_match_info(teams=self.tlas[4:], is_scored=True),
                ],
                # -- we are here --
                [
                    # 2. Lower bracket -- losers from round 1
                    self.build_match_info(
                        teams=self.tlas[2:4] + self.tlas[6:],
                        is_scored=False,
                    ),
                ],
                [
                    # 3. Upper bracket -- winders from round 1
                    self.build_match_info(
                        teams=self.tlas[:2] + self.tlas[4:6],
                        is_scored=False,
                    ),
                ],
                [
                    # 4. Lower bracket -- winners from round 2 + losers from round 3
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
                [
                    # Final -- winners from round 3 + winners from round 4
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
            ],
            expected_knockouts=[
                frozenset(),    # before first round
                frozenset(),    # knocked out in round 1
                frozenset(),    # future
                frozenset(),
                frozenset(),
                frozenset(),
            ],
        )

    def test_double_elimination_after_second_round(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    # 1. Initial round -- everyone
                    self.build_match_info(teams=self.tlas[:4], is_scored=True),
                    self.build_match_info(teams=self.tlas[4:], is_scored=True),
                ],
                [
                    # 2. Lower bracket -- losers from round 1
                    self.build_match_info(
                        teams=self.tlas[2:4] + self.tlas[6:],
                        is_scored=True,
                    ),
                ],
                # -- we are here --
                [
                    # 3. Upper bracket -- winders from round 1
                    self.build_match_info(
                        teams=self.tlas[:2] + self.tlas[4:6],
                        is_scored=False,
                    ),
                ],
                [
                    # 4. Lower bracket -- winners from round 2 + losers from round 3
                    self.build_match_info(
                        teams=self.tlas[2:4] + [UNKNOWABLE_TEAM] * 2,
                        is_scored=False,
                    ),
                ],
                [
                    # Final -- winners from round 3 + winners from round 4
                    self.build_match_info(teams=[UNKNOWABLE_TEAM] * 4, is_scored=False),
                ],
            ],
            expected_knockouts=[
                frozenset(),    # before first round
                frozenset(),    # knocked out in round 1
                frozenset(self.tlas[6:]),   # knocked out in round 2
                frozenset(),    # future
                frozenset(),
                frozenset(),
            ],
        )

    def test_double_elimination_after_third_round(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    # 1. Initial round -- everyone
                    self.build_match_info(teams=self.tlas[:4], is_scored=True),
                    self.build_match_info(teams=self.tlas[4:], is_scored=True),
                ],
                [
                    # 2. Lower bracket -- losers from round 1
                    self.build_match_info(
                        teams=self.tlas[2:4] + self.tlas[6:],
                        is_scored=True,
                    ),
                ],
                [
                    # 3. Upper bracket -- winders from round 1
                    self.build_match_info(
                        teams=self.tlas[:2] + self.tlas[4:6],
                        is_scored=True,
                    ),
                ],
                # -- we are here --
                [
                    # 4. Lower bracket -- winners from round 2 + losers from round 3
                    self.build_match_info(
                        teams=self.tlas[2:4] + self.tlas[4:6],
                        is_scored=False,
                    ),
                ],
                [
                    # Final -- winners from round 3 + winners from round 4
                    self.build_match_info(
                        teams=self.tlas[:2] + [UNKNOWABLE_TEAM] * 2,
                        is_scored=False,
                    ),
                ],
            ],
            expected_knockouts=[
                frozenset(),    # before first round
                frozenset(),    # knocked out in round 1
                frozenset(self.tlas[6:]),   # knocked out in round 2
                frozenset(),    # knocked out in round 3
                frozenset(),    # future
                frozenset(),
            ],
        )

    def test_double_elimination_after_fourth_round(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    # 1. Initial round -- everyone
                    self.build_match_info(teams=self.tlas[:4], is_scored=True),
                    self.build_match_info(teams=self.tlas[4:], is_scored=True),
                ],
                [
                    # 2. Lower bracket -- losers from round 1
                    self.build_match_info(
                        teams=self.tlas[2:4] + self.tlas[6:],
                        is_scored=True,
                    ),
                ],
                [
                    # 3. Upper bracket -- winders from round 1
                    self.build_match_info(
                        teams=self.tlas[:2] + self.tlas[4:6],
                        is_scored=True,
                    ),
                ],
                [
                    # 4. Lower bracket -- winners from round 2 + losers from round 3
                    self.build_match_info(
                        teams=self.tlas[2:4] + self.tlas[4:6],
                        is_scored=True,
                    ),
                ],
                # -- we are here --
                [
                    # Final -- winners from round 3 + winners from round 4
                    self.build_match_info(
                        teams=self.tlas[:2] + self.tlas[2:4] * 2,
                        is_scored=False,
                    ),
                ],
            ],
            expected_knockouts=[
                frozenset(),    # before first round
                frozenset(),    # knocked out in round 1
                frozenset(self.tlas[6:]),   # knocked out in round 2
                frozenset(),    # knocked out in round 3
                frozenset(self.tlas[4:6]),  # knocked out in round 4
                frozenset(),    # future
            ],
        )

    def test_double_elimination_after_final(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    # 1. Initial round -- everyone
                    self.build_match_info(teams=self.tlas[:4], is_scored=True),
                    self.build_match_info(teams=self.tlas[4:], is_scored=True),
                ],
                [
                    # 2. Lower bracket -- losers from round 1
                    self.build_match_info(
                        teams=self.tlas[2:4] + self.tlas[6:],
                        is_scored=True,
                    ),
                ],
                [
                    # 3. Upper bracket -- winders from round 1
                    self.build_match_info(
                        teams=self.tlas[:2] + self.tlas[4:6],
                        is_scored=True,
                    ),
                ],
                [
                    # 4. Lower bracket -- winners from round 2 + losers from round 3
                    self.build_match_info(
                        teams=self.tlas[2:4] + self.tlas[4:6],
                        is_scored=True,
                    ),
                ],
                [
                    # Final -- winners from round 3 + winners from round 4
                    self.build_match_info(
                        teams=self.tlas[:2] + self.tlas[2:4],
                        is_scored=True,
                    ),
                ],
                # -- we are here --
            ],
            expected_knockouts=[
                frozenset(),    # before first round
                frozenset(),    # knocked out in round 1
                frozenset(self.tlas[6:]),   # knocked out in round 2
                frozenset(),    # knocked out in round 3
                frozenset(self.tlas[4:6]),  # knocked out in round 4
                frozenset(self.tlas[:4]),   # everyone is knocked out in final (not shown)
            ],
        )
