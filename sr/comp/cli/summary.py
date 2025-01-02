from __future__ import annotations

import argparse
import datetime
from collections.abc import Mapping


def first(iterable):
    return next(i for i in iterable)


def counter_to_string(cntr):
    string = ", ".join("{1} {0}".format(*item) for item in cntr.items())
    return string


def format_duration(delta: datetime.timedelta) -> str:
    seconds = delta.total_seconds()
    if seconds.is_integer():
        seconds = int(seconds)
    return f'{seconds}s'


def command(args: argparse.Namespace) -> None:
    from collections import Counter

    from sr.comp.comp import SRComp

    comp = SRComp(args.compstate)

    print("Number of arenas: {} ({})".format(
        len(comp.arenas),
        ", ".join(comp.arenas.keys()),
    ))

    print("Number of teams: {} ({} rookies)".format(
        len(comp.teams),
        sum(1 for t in comp.teams.values() if t.rookie),
    ))

    slots_by_type = Counter(
        first(slot.values()).type.value
        for slot in comp.schedule.matches
    )
    slots_by_type_str = counter_to_string(slots_by_type)

    assert sum(slots_by_type.values()) == len(comp.schedule.matches)

    print("Number of match slots: {} ({})".format(
        len(comp.schedule.matches),
        slots_by_type_str,
    ))

    games_by_type = Counter(
        game.type.value
        for slot in comp.schedule.matches
        for game in slot.values()
    )
    games_by_type_str = counter_to_string(games_by_type)

    print("Number of games: {} ({})".format(
        sum(games_by_type.values()),
        games_by_type_str,
    ))

    durations: Mapping[str, datetime.timedelta] = comp.schedule.match_slot_lengths

    print("Match duration: {} (pre: {}, match: {}, post: {})".format(
        format_duration(durations['total']),
        format_duration(durations['pre']),
        format_duration(durations['post']),
        format_duration(durations['match']),
    ))


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg = "Show summary data about a compstate."

    parser = subparsers.add_parser('summary', help=help_msg, description=help_msg)
    parser.add_argument('compstate', help="competition state repository")
    parser.set_defaults(func=command)
