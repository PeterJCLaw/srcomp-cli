from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr.comp.match_period import MatchSlot


def format_time(delta: datetime.timedelta) -> str:
    seconds = int(delta.total_seconds() // 1 % 60)
    minutes = int((delta.total_seconds() // 60) % 60)
    hours = int(delta.total_seconds() // (60 * 60))

    return f'{hours}:{minutes:0>2}:{seconds:0>2}'


def _start_time(slot: MatchSlot) -> datetime.datetime:
    match, *_ = slot.values()
    return match.start_time


def command(settings: argparse.Namespace) -> None:
    from sr.comp.comp import SRComp

    offset = datetime.timedelta(seconds=settings.offset_seconds)
    match_number: int = settings.match_number

    comp = SRComp(settings.compstate)

    slots = comp.schedule.matches[match_number:]

    # Yes, this doesn't account for the game not aligning within the slot.
    # Happily we don't need to account for that explicitly as it's a fixed
    # offset which affects all matches equally and thus drops out.
    start_time = _start_time(slots[0])
    stream_start = start_time - offset

    print(f"{format_time(datetime.timedelta())} Introduction")

    last_end_time = start_time
    for slot in slots:
        match_teams = []
        for match in slot.values():
            opponents = [x for x in match.teams if x is not None]
            if not opponents:
                raise ValueError(f"Match {match.display_name} has no teams!")

            match_teams.append(" vs ".join(opponents))

        slot_teams = " | ".join(match_teams)

        if match.start_time > last_end_time:
            gap_steam_time = format_time(last_end_time - stream_start)
            gap_duration = format_time(match.start_time - last_end_time)
            print(f"{gap_steam_time}: Gap ({gap_duration})")

        match_steam_time = format_time(match.start_time - stream_start)
        print(f"{match_steam_time} {match.display_name}: {slot_teams}")

        last_end_time = match.end_time

    post_stream_time = format_time(match.end_time - stream_start)
    print(f"{post_stream_time}: After matches (Note: add details here)")

    sys.stdout.flush()
    print("Note: review to remove small gaps!", file=sys.stderr)
    print("Note: also add the outtro/wrapup!", file=sys.stderr)


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg = (
        "Determine the \"chapter\" timings for a Youtube livestream based "
        "on the match timings."
    )
    parser = subparsers.add_parser(
        'youtube-chapters',
        help=help_msg,
        description=help_msg,
    )
    parser.add_argument(
        'compstate',
        help="Competition state repo",
        type=Path,
    )
    parser.add_argument(
        'offset_seconds',
        type=int,
        help=(
            "The offset from the start of the video at which the first match "
            "starts. Hint: pause at the start of the match, then use 'Copy video "
            "URL at current time' and extract the value of the 't' argument from "
            "the query string."
        ),
    )
    parser.add_argument(
        'match_number',
        type=int,
        help="The match number to start at. (default: %(default)s)",
        default=0,
        nargs=argparse.OPTIONAL,
    )
    parser.set_defaults(func=command)
