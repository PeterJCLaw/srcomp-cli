from __future__ import annotations

import dataclasses
import unittest
from collections.abc import Collection, Mapping, Sequence

from sr.comp.cli.knocked_out_teams import teams_and_rounds
from sr.comp.knockout_scheduler import UNKNOWABLE_TEAM
from sr.comp.match_period import Match
from sr.comp.teams import Team
from sr.comp.types import MatchNumber, TLA

from .factories import build_match


@dataclasses.dataclass(frozen=True)
class FakeSchedule:
    knockout_rounds: Sequence[Sequence[Match]]
    n_league_matches: int


class TestKnockedOutTeams(unittest.TestCase):
    maxDiff = None

    def get_team(self, tla: str, dropped_out_after: MatchNumber | None = None) -> Team:
        return Team(TLA(tla), f"Team {tla}", rookie=False, dropped_out_after=dropped_out_after)

    def get_teams(self, tlas: Collection[str]) -> Mapping[TLA, Team]:
        return {TLA(x): self.get_team(x) for x in tlas}

    def assertKnockedOutTeams(
        self,
        knockout_rounds: Sequence[Sequence[Match]],
        expected_knockouts: list[frozenset[TLA]],
    ) -> None:
        result = list(teams_and_rounds(
            self.teams,
            FakeSchedule(
                knockout_rounds=knockout_rounds,
                n_league_matches=1,
            ),
        ))

        self.assertEqual(
            expected_knockouts,
            [x.teams_out for x in result],
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

    def test_league_not_finished(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    build_match(teams=[UNKNOWABLE_TEAM] * 4),
                    build_match(teams=[UNKNOWABLE_TEAM] * 4),
                ],
                [
                    build_match(teams=[UNKNOWABLE_TEAM] * 4),
                ],
            ],
            expected_knockouts=[
                frozenset(self.tlas),
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
                    build_match(teams=[UNKNOWABLE_TEAM] * 4),
                    build_match(teams=[UNKNOWABLE_TEAM] * 4),
                ],
                [
                    build_match(teams=[UNKNOWABLE_TEAM] * 4),
                ],
            ],
            expected_knockouts=[
                frozenset(self.tlas) - frozenset([team.tla]),
                frozenset(),
            ],
        )

    def test_league_just_finished(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    build_match(teams=self.tlas[:4]),
                    build_match(teams=self.tlas[4:]),
                ],
                [
                    build_match(teams=[UNKNOWABLE_TEAM] * 4),
                ],
            ],
            expected_knockouts=[
                frozenset(),
                frozenset(self.tlas),
            ],
        )

    def test_after_first_round(self) -> None:
        self.assertKnockedOutTeams(
            knockout_rounds=[
                [
                    build_match(teams=self.tlas[:4]),
                    build_match(teams=self.tlas[4:]),
                ],
                [
                    build_match(teams=self.tlas[2:6]),
                ],
            ],
            expected_knockouts=[
                frozenset(),
                frozenset(self.tlas[:2] + self.tlas[-2:]),
            ],
        )
