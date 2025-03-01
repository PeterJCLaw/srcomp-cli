from __future__ import annotations

import collections
from typing import Collection, Iterator, Mapping, Sequence, TypeVar

from sr.comp.types import ArenaName, MatchNumber, TLA

from . import loading
from .types import BadMatch, Configuration, ID, RawMatch

T = TypeVar('T')


def chunks_of_size(list_: list[T], size: int) -> Iterator[list[T]]:
    if len(list_) % size != 0:
        raise ValueError(
            "Unable to chunk list whose size is not evenly divisble by given "
            f"size {size}.",
        )

    list_ = list_[:]
    while len(list_):
        chunk = []
        for _ in range(size):
            chunk.append(list_.pop(0))
        yield chunk


def ignore_ids(ids: list[ID], ids_to_remove: list[ID]) -> None:
    for i in ids_to_remove:
        ids.remove(i)


def get_id_subsets(ids: Collection[T], limit: int) -> Iterator[Collection[T]]:
    num_ids = len(ids)

    extra = num_ids - limit

    if extra == 0:
        # Only one possibility -- use all of them
        yield ids

    elif extra == 1:
        for idx in range(len(ids)):
            ids_clone = list(ids)
            ids_clone.pop(idx)
            yield ids_clone

    elif extra == 2:
        for idx1 in range(len(ids)):
            for idx2 in range(idx1 + 1, len(ids)):
                ids_clone = list(ids)
                ids_clone.pop(idx2)
                ids_clone.pop(idx1)
                yield ids_clone

    elif extra == 3:
        for idx1 in range(len(ids)):
            for idx2 in range(idx1 + 1, len(ids)):
                for idx3 in range(idx2 + 1, len(ids)):
                    ids_clone = list(ids)
                    ids_clone.pop(idx3)
                    ids_clone.pop(idx2)
                    ids_clone.pop(idx1)
                    yield ids_clone

    else:
        # TODO: consider generalising the above or adding more handling
        raise Exception(f"Too many empty slots to compensate for ({extra}).")


def build_id_team_maps(ids: list[ID], team_ids: Sequence[TLA]) -> Iterator[dict[ID, TLA]]:
    # If there are more ids than team_ids we want to ensure that we minimize
    # the number of matches which have empty places and also the number of
    # empty places in any given match.
    # This function generates possible mappings of ids to teams as needed
    # in order to explore excluding different ids.
    #
    # Note: this function does _not_ explore mapping the same subset of
    # ids to the given teams since that doesn't achieve any changes in
    # which matches have empty spaces.

    for id_subset in get_id_subsets(ids, len(team_ids)):
        yield dict(zip(id_subset, team_ids))


def build_matches(
    id_team_map: dict[ID, TLA],
    schedule: list[list[ID]],
    arena_ids: Collection[ArenaName],
    teams_per_game: int,
    first_match_number: int,
) -> tuple[
    dict[MatchNumber, RawMatch],
    list[BadMatch],
]:
    matches = {}
    bad_matches = []
    for match_num, match_ids in enumerate(schedule, start=first_match_number):
        match_teams = [id_team_map.get(id_) for id_ in match_ids]
        games = chunks_of_size(match_teams, teams_per_game)

        matches[MatchNumber(match_num)] = match = dict(zip(arena_ids, games))

        # Check that the match has enough actual teams; warn if not
        for arena, teams in match.items():
            num_teams = len(set(teams) - set([None]))
            if num_teams <= (teams_per_game / 2):
                bad_matches.append(BadMatch(arena, MatchNumber(match_num), num_teams))

    return matches, bad_matches


def are_better_matches(
    best: list[BadMatch],
    new: list[BadMatch],
    teams_per_game: int,
) -> bool:
    def get_empty_places_map(bad_matches: list[BadMatch]) -> Mapping[int, int]:
        empty_places_map: dict[int, int] = collections.Counter()
        for bad_match in bad_matches:
            num_empty = teams_per_game - bad_match.num_teams
            empty_places_map[num_empty] += 1
        return empty_places_map

    best_map = get_empty_places_map(best)
    new_map = get_empty_places_map(new)

    possible_empty_places = set(list(best_map.keys()) + list(new_map.keys()))

    # Even single matches with lots of empty slots are bad
    for num_empty_places in sorted(possible_empty_places, reverse=True):
        if new_map[num_empty_places] < best_map[num_empty_places]:
            return True

    return False


def get_best_fit(
    config: Configuration,
    ids: list[ID],
    schedule: list[list[ID]],
) -> tuple[
    dict[MatchNumber, RawMatch],
    list[BadMatch],
]:
    best: tuple[
        dict[MatchNumber, RawMatch],
        list[BadMatch],
    ] | None = None
    for id_team_map in build_id_team_maps(ids, config.team_ids):
        matches, bad_matches = build_matches(
            id_team_map,
            schedule,
            config.arena_ids,
            config.teams_per_game,
            config.first_match_number,
        )

        if len(bad_matches) == 0:
            # Nothing bad about these, ship them
            return matches, bad_matches

        if best is None or are_better_matches(best[1], bad_matches, config.teams_per_game):
            best = (matches, bad_matches)

    assert best is not None

    return best


def build_schedule(
    config: Configuration,
    schedule_lines: list[str],
    ids_to_ignore: list[ID],
) -> tuple[
    dict[MatchNumber, RawMatch],
    list[BadMatch],
]:
    # Collect up the ids used
    ids, schedule = loading.load_ids_schedule(
        schedule_lines,
        num_arenas=config.num_arenas,
        teams_per_game=config.teams_per_game,
    )

    # Ignore any ids we've been told to
    if ids_to_ignore:
        ignore_ids(ids, ids_to_ignore)

    # Quality/intent checks
    if len(ids) > config.num_teams:
        print(
            f"Warning: more places than teams ({len(ids)} places, {config.num_teams} teams). "
            "Heuristics will be used to attempt to minimise the number of empty "
            "spaces in matches when mapping teams to places.",
        )
        if not ids_to_ignore:
            print(
                "Consider using `--ignore-ids` to indicate which ids should be "
                "ignored if the default logic does not choose the right ones.",
            )

    # Sanity checks
    if len(ids) < config.num_teams:
        raise ValueError(
            f"Not enough places in the schedule (need {config.num_teams}, got {len(ids)}).",
        )

    # Get matches
    matches, bad_matches = get_best_fit(config, ids, schedule)

    return matches, bad_matches
