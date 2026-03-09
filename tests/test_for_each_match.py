import argparse
import contextlib
import io
import unittest
from pathlib import Path
from unittest import mock

from sr.comp.cli.for_each_match import (
    command,
    PlaceholderExpander,
    replace_placeholders,
)
from sr.comp.types import TLA

from .factories import build_match


class ForEachMatchTests(unittest.TestCase):
    longMessage = True
    maxDiff = None

    def test_smoke(self) -> None:
        compstate_path = str(Path(__file__).parent / 'dummy')

        settings = argparse.Namespace(
            compstate=compstate_path,
            arena=None,
            matches=set([0, 2, 3]),
            command=['spam', '{TYPE}:{ARENA}', '{NUMBER}|{TLAS}'],
        )

        with mock.patch('subprocess.check_call') as mock_check_call:
            command(settings)

        mock_check_call.assert_has_calls([
            mock.call(['spam', 'league:A', '0|- CLY TTN -']),
            mock.call(['spam', 'league:B', '0|GRS QMC - -']),
            mock.call(['spam', 'league:A', '2|ICE MFG SWI BRN']),
            mock.call(['spam', 'league:B', '2|TBG EMM SGS GYG']),
            mock.call(['spam', 'league:A', '3|MAI2 HSO KDE CCR']),
            mock.call(['spam', 'league:B', '3|SCC LSS HZW MAI']),
        ])

    def test_validate_placeholders(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            PlaceholderExpander.validate('fine')
            self.assertEqual("", stderr.getvalue())

        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            PlaceholderExpander.validate('@unknown')
            self.assertEqual(
                "Warning: unrecognised value '@unknown'.\n",
                stderr.getvalue(),
            )

        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            PlaceholderExpander.validate('@TLAS')
            self.assertEqual("", stderr.getvalue())

    def test_replace_placeholders(self) -> None:
        match = build_match(num=42, teams=[TLA('ABC'), None])

        command = replace_placeholders(match, [
            'spam',
            '{NUMBER}:{ARENA}',
            '{TLAS}',
            '@TLAS',
            '@TLAS|',
        ])

        self.assertEqual(
            ['spam', '42:main', 'ABC -', 'ABC', '-', '@TLAS|'],
            command,
        )
