from __future__ import annotations

import argparse
import unittest

from sr.comp.cli.modernise_static_knockout import command

from .factories import dummy_compstate


class ModerniseStaticKnockoutTests(unittest.TestCase):
    maxDiff = None

    def test_already_modernised(self) -> None:
        with dummy_compstate(
            revision='b03776b785125c7e6fa15ed32f309fbaab0279ff',
        ) as compstate_path:
            original = (compstate_path / 'schedule.yaml').read_text()

            command(argparse.Namespace(compstate=compstate_path))

            new = (compstate_path / 'schedule.yaml').read_text()

            self.assertEqual(original, new, "Should not have modified already valid file")

    def test_modernise(self) -> None:
        with dummy_compstate(
            revision='76d8378253e71a1366b4c42b16c16df2f71fff2c',
        ) as compstate_path:
            expected = (compstate_path / 'schedule.yaml').read_text()

        with dummy_compstate(
            revision='1d346d9a6ce12bb5eae34f08e7296fa335f1cfd4',
        ) as compstate_path:
            command(argparse.Namespace(compstate=compstate_path))

            new = (compstate_path / 'schedule.yaml').read_text()

            self.assertEqual(
                expected,
                new,
                "Should not have modified already valid file",
            )
