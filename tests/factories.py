from __future__ import annotations

import contextlib
import datetime
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Sequence

from dateutil.tz import UTC

from sr.comp.match_period import Match, MatchType
from sr.comp.types import ArenaName, MatchNumber, TLA

_DEFAULT_START_TIME = datetime.datetime(2020, 1, 25, 11, 0, tzinfo=UTC)
_DEFAULT_END_TIME = datetime.datetime(2020, 1, 25, 11, 5, tzinfo=UTC)


def build_match(
    num: int = 0,
    arena: str = 'main',
    teams: Sequence[TLA | None] = (),
    start_time: datetime.datetime = _DEFAULT_START_TIME,
    end_time: datetime.datetime = _DEFAULT_END_TIME,
    type_: MatchType = MatchType.league,
    use_resolved_ranking: bool = False,
) -> Match:
    return Match(
        MatchNumber(num),
        f"Match {num}",
        ArenaName(arena),
        list(teams),
        start_time,
        end_time,
        type_,
        use_resolved_ranking,
    )


@contextlib.contextmanager
def dummy_compstate(revision: str | None = None) -> Iterator[Path]:
    REF_COMPSTATE = Path(__file__).parent / 'dummy'

    with tempfile.TemporaryDirectory() as tempdir:
        def _git(*args: str | Path) -> None:
            subprocess.check_call(
                ['git', *args],
                env={'GIT_ADVICE': "0"},
                cwd=tempdir,
            )

        _git('clone', '--quiet', REF_COMPSTATE, tempdir)
        if revision is not None:
            _git('checkout', '--quiet', revision)

        yield Path(tempdir)
