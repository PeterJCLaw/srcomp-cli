from __future__ import annotations

import argparse
import enum

DISPLAY_NAME_WIDTH = 18


class SecondsOption(enum.Enum):
    ALWAYS = 'always'
    NEVER = 'never'
    AUTO = 'auto'

    def __str__(self) -> str:
        return self.value


def first(iterable):
    return next(i for i in iterable)


def command(settings: argparse.Namespace) -> None:
    import os.path
    from datetime import datetime, timedelta

    from sr.comp.comp import SRComp
    from sr.comp.match_operations import MatchState

    comp = SRComp(os.path.realpath(settings.compstate))

    num_teams_per_arena = getattr(comp, 'num_teams_per_arena', len(comp.corners))

    matches = comp.schedule.matches
    now = datetime.now(comp.timezone)
    current_matches = comp.operations.get_matches_at(now).matches

    if not settings.all:
        if current_matches:
            time = min(x.start_time for x in current_matches)
        else:
            time = now
        time -= timedelta(minutes=10)

        matches = [
            slot
            for slot in matches
            if first(slot.values()).start_time >= time
        ]

        matches = matches[:int(settings.limit)]

    def teams_str(teams):
        return ":".join(tla.center(5) if tla else "  -  " for tla in teams)

    def print_col(text, last=False):
        print(text, end='|')

    def should_show_seconds() -> bool:
        if settings.seconds == SecondsOption.ALWAYS:
            return True
        if settings.seconds == SecondsOption.NEVER:
            return False

        assert settings.seconds == SecondsOption.AUTO
        for slot in matches:
            for match in slot.values():
                if match.start_time.second != 0:
                    return True

        return False

    time_format = '%H:%M'
    time_space = ""
    if should_show_seconds():
        time_format += ':%S'
        time_space = "   "

    empty_teams = teams_str(" " * num_teams_per_arena)
    teams_len = len(empty_teams)

    print_col(f" Num Time  {time_space}")
    for a in comp.arenas.values():
        print_col(a.display_name.center(teams_len))
    print_col("Display Name".center(DISPLAY_NAME_WIDTH))
    print()

    arena_ids = comp.arenas.keys()
    for slot in matches:
        m = first(slot.values())
        print_col(f" {m.num:>3} {m.start_time:{time_format}} ")

        for a_id in arena_ids:
            if a_id in slot:
                print_col(teams_str(slot[a_id].teams))
            else:
                print_col(empty_teams)

        print_col(m.display_name.center(DISPLAY_NAME_WIDTH))

        if m in current_matches:
            marker = " *"
            if comp.operations.get_match_state(m, now) == MatchState.HELD:
                marker += " [held]"
            print(marker)
        else:
            print()


def add_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    help_msg = "Show the match schedule."
    parser = subparsers.add_parser(
        'show-schedule',
        help=help_msg,
        description=help_msg,
    )
    parser.add_argument(
        'compstate',
        help="competition state repo",
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help="show all matches, not just the upcoming ones (ignores --limit)",
    )
    parser.add_argument(
        '--seconds',
        help="show times including seconds",
        choices=SecondsOption,
        type=SecondsOption,
        default=SecondsOption.AUTO,
    )
    parser.add_argument(
        '--limit',
        default=15,
        help="how many matches to show (default: %(default)s)",
    )
    parser.set_defaults(func=command)
