from __future__ import annotations

import argparse
from pathlib import Path

from sr.comp.types import TLA


def round_name(rounds_left: int) -> str:
    if rounds_left == 0:
        return "Finals"
    elif rounds_left == 1:
        return "Semi Finals"
    elif rounds_left == 2:
        return "Quarter Finals"
    return ""


def command(settings: argparse.Namespace) -> None:
    from sr.comp.comp import SRComp

    comp = SRComp(settings.compstate)

    teams_last_round: set[TLA | None] = set()
    last_round_num = len(comp.schedule.knockout_rounds) - 1
    for i, matches in enumerate(comp.schedule.knockout_rounds):
        teams_this_round = set()
        for game in matches:
            teams_this_round.update(game.teams)

        print(f"## Teams not in round {i} ({round_name(last_round_num - i)})")
        print()
        out = teams_last_round - teams_this_round
        teams_out = [t for t in out if t is not None]
        for tla in teams_out:
            print(tla, comp.teams[tla].name)
        teams_last_round = teams_this_round
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
    parser.set_defaults(func=command)
