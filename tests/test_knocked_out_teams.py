from __future__ import annotations

import dataclasses
import unittest
from collections.abc import Collection, Mapping, Sequence

from sr.comp.cli.knocked_out_teams import Round, teams_and_rounds
from sr.comp.match_period import Match, MatchSlot
from sr.comp.teams import Team
from sr.comp.types import MatchNumber, TLA


@dataclasses.dataclass(frozen=True)
class FakeSchedule:
    knockout_rounds: Sequence[Sequence[Match]]
    matches: Sequence[MatchSlot]
    n_league_matches: int


class TestKnockedOutTeams(unittest.TestCase):
    def get_team(self, tla: str, dropped_out_after: MatchNumber | None = None) -> Team:
        return Team(TLA(tla), f"Team {tla}", rookie=False, dropped_out_after=dropped_out_after)

    def get_teams(self, tlas: Collection[str]) -> Mapping[TLA, Team]:
        return {TLA(x): self.get_team(x) for x in tlas}

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

    def test_league_not_finished(self) -> None:
        result = list(teams_and_rounds(
            self.teams,
            FakeSchedule(
                knockout_rounds=[],
                matches=[MatchSlot({})],
                n_league_matches=1,
            ),
            None,
        ))

        self.assertEqual([], result)
