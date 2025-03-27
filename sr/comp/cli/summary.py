from __future__ import annotations

import argparse
import datetime
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import TypeVar

from sr.comp.match_period import MatchPeriod

T = TypeVar('T')


def first(iterable: Iterable[T]) -> T:
    return next(i for i in iterable)


def counter_to_string(cntr: Counter[T]) -> str:
    string = ", ".join("{1} {0}".format(*item) for item in cntr.items())
    return string


def format_duration(delta: datetime.timedelta) -> str:
    seconds = delta.total_seconds()
    if seconds.is_integer():
        seconds = int(seconds)
    return f'{seconds}s'


def format_period(period: MatchPeriod, match_duration: datetime.timedelta) -> str:
    fmt = '%H:%M'

    if period.matches:
        last_match = first(period.matches[-1].values())
        last_match_end = f"matches end {last_match.end_time:{fmt}}"
    else:
        last_match_end = "[no matches]"

    date = period.start_time.date()
    desc = period.description

    max_end_time = period.max_end_time + match_duration
    timings = f"{period.start_time:{fmt}}–{max_end_time:{fmt}}, {last_match_end}"

    return f"{date} {desc} ({timings})"


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
    match_duration = durations['total']

    print("Match duration: {} (pre: {}, match: {}, post: {})".format(
        format_duration(match_duration),
        format_duration(durations['pre']),
        format_duration(durations['post']),
        format_duration(durations['match']),
    ))

    print("Match periods:")
    for period in comp.schedule.match_periods:
        print(f' · {format_period(period, match_duration)}')

    print("Last scored match: {}".format(comp.scores.last_scored_match))


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg = "Show summary data about a compstate."

    parser = subparsers.add_parser('summary', help=help_msg, description=help_msg)
    parser.add_argument('compstate', help="competition state repository")
    parser.set_defaults(func=command)
