from __future__ import annotations

import argparse
import datetime
from pathlib import Path
from typing import Any, Callable

time_parse_pattern = r'^((?P<hours>\d+?)hr)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?$'


class BadDurationException(ValueError):
    def __init__(self, time_str: str) -> None:
        msg = f"Unable to parse duration string '{time_str}'."
        super().__init__(msg)


def parse_duration(time_str: str) -> datetime.timedelta:
    import re

    parts = re.match(time_parse_pattern, time_str)
    if not parts:
        if not time_str.isdigit():
            raise BadDurationException(time_str)
        else:
            s = int(time_str)
            return datetime.timedelta(seconds=s)

    time_params = {}
    for (name, param) in parts.groupdict().items():
        if param:
            time_params[name] = int(param)

    return datetime.timedelta(**time_params)


def parse_datetime(when_str: str) -> datetime.datetime:
    import re

    from dateutil.parser import parse as parse_date
    from dateutil.tz import tzlocal

    def parse_now(match: re.Match[str]) -> datetime.datetime:
        return datetime.datetime.now()

    def parse_future(match: re.Match[str]) -> datetime.datetime:
        offset = parse_duration(match.group(1))
        return datetime.datetime.now() + offset

    def parse_past(match: re.Match[str]) -> datetime.datetime:
        offset = parse_duration(match.group(1))
        return datetime.datetime.now() - offset

    def parse_absolute(match: re.Match[str]) -> datetime.datetime:
        return parse_date(match.group(0))

    DATETIME_PATTERNS: list[tuple[str, Callable[[re.Match[str]], datetime.datetime]]] = [
        (r'^([^ ]+)\s*ago$', parse_past),
        (r'^in\s*([^ ]+)$', parse_future),
        (r'^now$', parse_now),
        (r'^.+$', parse_absolute),
    ]

    for pattern, parse_fn in DATETIME_PATTERNS:
        match = re.match(pattern, when_str)
        if match is None:
            continue
        try:
            when = parse_fn(match)
            break
        except ValueError:
            continue
    else:
        raise ValueError(
            f"Unable to parse date string: {when_str!r}",
        )

    # Timezone information gets ignored, and the resulting datetime is
    # timezone-unaware. However the compstate needs timezone data to be
    # present.
    # Assume that the user wants their current timezone.
    when = when.replace(tzinfo=tzlocal())
    return when


def get_current_match_start(compstate_path: Path) -> datetime.datetime:
    from sr.comp.comp import SRComp
    compstate = SRComp(compstate_path)
    now = compstate.schedule.datetime_now
    current_matches = tuple(compstate.schedule.matches_at(now))
    if not current_matches:
        raise Exception("Not currently in a match, specify a valid time instead")

    return min(x.start_time for x in current_matches)


def parse_time(compstate_path: Path, when_str: str) -> datetime.datetime:
    if when_str == "current match":
        return get_current_match_start(compstate_path)
    else:
        return parse_datetime(when_str)


def add_delay(schedule: dict[str, Any], delay_seconds: int, when: datetime.datetime) -> None:
    delays = schedule.get('delays')
    if not delays:
        delays = schedule['delays'] = []
    new_delay = {
        'delay': delay_seconds,
        'time': when,
    }
    delays.append(new_delay)


def command(settings: argparse.Namespace) -> tuple[datetime.timedelta, datetime.datetime]:
    from sr.comp.cli import yaml_round_trip as yaml

    with yaml.edit(settings.compstate / 'schedule.yaml') as schedule:
        how_long = parse_duration(settings.how_long)
        how_long_seconds = how_long.seconds

        when = parse_time(settings.compstate, settings.when)
        when = when.replace(microsecond=0)

        add_delay(schedule, how_long_seconds, when)

    return how_long, when


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        'how_long',
        help=(
            "How long to delay the competition for. Specify either as a number "
            "of seconds or as a string of the form 1m30s."
        ),
    )
    parser.add_argument(
        'when',
        nargs='?',
        default='now',
        help=(
            "When the delay should occur. This can be specified in a number of "
            "formats: an absolute time (parsed by dateutil), 'now', "
            "'current match' (the start of the current match slot), "
            "'<duration> ago' or 'in <duration>' where <duration> is specified "
            "as a number of seconds or a string of the form 1m30s. "
            "Assumes all times are in the current timezone, regardless of input."
        ),
    )


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg = "Add a delay the competition state."
    parser = subparsers.add_parser(
        'add-delay',
        help=help_msg,
        description=help_msg,
    )
    parser.add_argument(
        'compstate',
        type=Path,
        help="competition state repository",
    )
    add_arguments(parser)
    parser.set_defaults(func=command)
