from typing import Dict, List, Mapping, NamedTuple, Optional

from sr.comp.comp import SRComp
from sr.comp.match_period import Match, MatchSlot
from sr.comp.scores import BaseScores, LeaguePosition
from sr.comp.types import ArenaName, GamePoints, MatchNumber, TLA

__description__ = "Show the game and league points achieved for each match"
DISPLAYED_ZONES = 2


class MatchCorner(NamedTuple):
    tla: Optional[TLA]
    ranking: Optional[LeaguePosition]
    game: Optional[GamePoints]
    league: Optional[int]


class MatchResult(NamedTuple):
    num: MatchNumber
    arena: ArenaName
    display_name: str
    corners: Dict[int, MatchCorner]


def collect_match_info(comp: SRComp, match: Match) -> MatchResult:
    from sr.comp.match_period import MatchType
    from sr.comp.scores import degroup

    score_data: BaseScores
    league_points: Mapping[TLA, Optional[int]]
    game_points: Mapping[TLA, Optional[GamePoints]]
    ranking: Mapping[TLA, Optional[LeaguePosition]]

    if match.type == MatchType.knockout:
        score_data = comp.scores.knockout
    elif match.type == MatchType.tiebreaker:
        score_data = comp.scores.tiebreaker
    elif match.type == MatchType.league:
        score_data = comp.scores.league

    match_id = (match.arena, match.num)

    if match_id in score_data.game_points:
        league_points = score_data.ranked_points[match_id]
        game_points = score_data.game_points[match_id]
        ranking = degroup(score_data.game_positions[match_id])
    else:
        league_points = {}
        game_points = {}
        ranking = {}
        for team in match.teams:
            if team is not None:
                league_points[team] = None
                game_points[team] = None
                ranking[team] = None

    corner_data: Dict[int, MatchCorner] = {}

    for corner, team in enumerate(match.teams):
        match_id = (match.arena, match.num)

        if team:  # corner occupied
            corner_data[corner] = MatchCorner(
                tla=team,
                ranking=ranking[team],
                game=game_points[team],
                league=league_points[team],
            )
        else:
            corner_data[corner] = MatchCorner(
                tla=None,
                ranking=None,
                game=None,
                league=None,
            )

    return MatchResult(
        num=match.num,
        arena=match.arena,
        display_name=match.display_name,
        corners=corner_data,
    )


def match_index(matches: List[MatchSlot], match_num: int) -> int:
    "Returns the index of the first slot that contains the given match number"
    for idx, slots in enumerate(matches):
        for match in slots.values():
            if match.num == match_num:
                return idx

    # if no match is found use the last one
    return idx


def generate_displayed_headings(num_corners: int) -> List[str]:
    displayed_heading = ["Match"]

    for _ in range(num_corners):
        displayed_heading.append("Zone")
        displayed_heading.append("TLA")
        displayed_heading.append("Rank")
        displayed_heading.append("Game")
        displayed_heading.append("League")

    return displayed_heading


def generate_displayed_match(match: MatchResult, num_corners: int) -> List[List[str]]:
    displayed_match = []
    displayed_corners = []

    for zone, (tla, ranking, game, league) in match.corners.items():
        displayed_corner: List[str] = []

        displayed_corner.append(str(zone))
        if tla is not None:
            displayed_corner.append(tla)
            displayed_corner.append("??" if ranking is None else str(ranking))
            displayed_corner.append("??" if game is None else str(game))
            displayed_corner.append("??" if league is None else str(league))
        else:
            displayed_corner.extend(['', '', '', ''])

        displayed_corners.append(displayed_corner)

    # wrap the number of zones to the DISPLAYED_ZONES constant
    for corner in range(0, num_corners, DISPLAYED_ZONES):
        # first row displays the match and arena information,
        # any extra rows leave this field blank
        if corner == 0:
            match_row = [f"{match.display_name} in {match.arena}"]
        else:
            match_row = [""]

        for idx in range(DISPLAYED_ZONES):
            try:
                match_row.extend(displayed_corners[corner + idx])
            except IndexError:
                # pad the number of corners out to a multiple of DISPLAYED_ZONES
                match_row.extend(['', '', '', ''])

        displayed_match.append(match_row)

    return displayed_match


def command(settings):
    import os.path

    from tabulate import tabulate

    comp = SRComp(os.path.realpath(settings.compstate))

    match_results: List[MatchResult] = []

    filter_tla = settings.tla
    skip_filter = True

    if filter_tla is not None:
        skip_filter = False
        # validate TLA exists
        if filter_tla not in comp.teams.keys():
            print('TLA not found')
            return

    if not settings.all and skip_filter:
        # get the index of the last scored match
        end_match = match_index(
            comp.schedule.matches,
            comp.scores.last_scored_match,
        ) + 1  # include last scored match in results
        scan_matches = comp.schedule.matches[
            max(0, end_match - int(settings.limit)):end_match
        ]
    else:
        scan_matches = comp.schedule.matches

    for slots in scan_matches:
        match_results.extend(
            collect_match_info(comp, match)
            for match in slots.values()
            if filter_tla in match.teams or skip_filter
        )

    if len(match_results) == 0:
        print("No matches found for current filters")
        return

    num_teams_per_arena = comp.num_teams_per_arena

    displayed_matches: List[List[str]] = []

    for match in match_results:
        displayed_matches.extend(generate_displayed_match(match, num_teams_per_arena))

    print(tabulate(
        displayed_matches,
        headers=generate_displayed_headings(DISPLAYED_ZONES),
        tablefmt='pretty',
        colalign=(
            ('center',) + ('right', 'center', 'right', 'right', 'right') * DISPLAYED_ZONES
        ),
    ))


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'show-match-scores',
        help=__description__,
        description=__description__,
    )
    parser.add_argument(
        'compstate',
        help="competition state repo",
    )
    parser.add_argument(
        'tla',
        nargs='?',
        help="filter to matches containing this TLA (ignores --limit)",
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help="show all matches (overrides --limit)",
    )
    parser.add_argument(
        '--limit',
        default=15,
        help="how many recently scored matches to show (default: %(default)s)",
    )
    parser.set_defaults(func=command)
