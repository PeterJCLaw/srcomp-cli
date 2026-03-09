from __future__ import annotations

import collections
import enum
from pathlib import Path

from sr.comp.types import TLA


class Strategy(enum.Enum):
    AUTO = 'auto'
    LAYOUT = 'layout'
    RANDOM = 'random'

    def __str__(self) -> str:
        return self.value


def order_teams_randomly(team_ids: list[TLA]) -> list[TLA]:
    """
    Order teams using our stable random logic.
    """
    from sr.comp.knockout_scheduler.stable_random import Random

    random = Random()
    random.seed("".join(team_ids).encode())
    random.shuffle(team_ids)
    return team_ids


def order_teams_by_location(layout_yaml: Path, team_ids: list[TLA]) -> list[TLA]:
    """
    Order teams by location, such that the order of appearances in the matches
    is equivalent to the ordering in the layout.

    This is useful as it should mean that the scrutineers can move around the
    venue easily visiting teams in the order which they first appear in matches.
    """
    from sr.comp.cli import yaml_round_trip as yaml
    from sr.comp.validation import join_and

    with open(layout_yaml) as lf:
        layout_raw = yaml.load(lf)
        layout = layout_raw['teams']

    ordered_teams = []
    for group in layout:
        ordered_teams += group['teams']

    layout_teams = set(ordered_teams)

    if len(layout_teams) != len(ordered_teams):
        duplicates = [x for x, y in collections.Counter(ordered_teams).items() if y > 1]
        raise ValueError(f"Some teams appear twice in the layout! {join_and(duplicates)}")

    all_teams = set(team_ids)
    missing = all_teams - layout_teams
    if missing:
        raise ValueError(f"Some teams not in layout: {join_and(missing)}.")

    extra = layout_teams - all_teams
    if extra:
        print(f"WARNING: Extra teams in layout will be ignored: {join_and(extra)}.")
        for tla in extra:
            ordered_teams.remove(tla)

    return ordered_teams


def order_teams(
    compstate_path: Path,
    team_ids: list[TLA],
    strategy: Strategy,
) -> list[TLA]:
    """
    Order teams either randomly or, if there's a layout available, by location.
    """
    layout_yaml = compstate_path / 'layout.yaml'

    if strategy == Strategy.RANDOM:
        return order_teams_randomly(team_ids)

    elif strategy == Strategy.LAYOUT:
        if not layout_yaml.exists():
            raise ValueError(
                "Unable to order teams by layout when there is no layout file",
            )

        return order_teams_by_location(layout_yaml, team_ids)

    elif strategy == Strategy.AUTO:
        if layout_yaml.exists():
            return order_teams_by_location(layout_yaml, team_ids)

        return order_teams_randomly(team_ids)

    raise AssertionError(
        "Invalid strategy selected. Did you add a new strategy but not add a handler?",
    )
