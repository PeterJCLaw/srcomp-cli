from __future__ import annotations

import argparse
import datetime
import io
import textwrap
import unittest
from pathlib import Path

from sr.comp.cli import yaml_round_trip as yaml
from sr.comp.cli.yaml_round_trip import command

from .factories import dummy_compstate


class RoundTripTests(unittest.TestCase):
    maxDiff = 8000

    def get_info(self, file_path: Path) -> tuple[float, str]:
        return file_path.stat().st_mtime, file_path.read_text()

    def test_dummy_schedule(self) -> None:
        with dummy_compstate() as compstate_path:
            # Assumes that the dummy schedule is already properly formatted
            dummy_schedule = compstate_path / 'schedule.yaml'

            orig_mod, orig_content = self.get_info(dummy_schedule)

            settings = argparse.Namespace(file_path=dummy_schedule)
            command(settings)

            new_mod, new_content = self.get_info(dummy_schedule)

            self.assertNotEqual(orig_mod, new_mod, "Should have rewritten the file")
            self.assertEqual(
                orig_content,
                new_content,
                "Should not have changed file content",
            )

    def test_timestamp_with_timezone(self) -> None:
        content = textwrap.dedent('''
            start: 2022-04-01 12:04:12+01:00
            end: 2022-04-01 12:05:37+01:00
        ''').lstrip()

        data = yaml.load(io.StringIO(content))

        tzinfo = datetime.timezone(offset=datetime.timedelta(hours=1))

        self.assertEqual(
            {
                'start': datetime.datetime(2022, 4, 1, 12, 4, 12, tzinfo=tzinfo),
                'end': datetime.datetime(2022, 4, 1, 12, 5, 37, tzinfo=tzinfo),
            },
            dict(data),
            "Should have parsed timezone aware times",
        )

        output = io.StringIO()
        yaml.dump(data, output)

        self.assertEqual(
            content,
            output.getvalue(),
            "Timestamps with timezones should round-trip",
        )

    def test_timestamp_with_timezone_updated(self) -> None:
        content = textwrap.dedent('''
            start: 2022-04-01 12:04:12+01:00
            end: 2022-04-01 12:05:37+01:00
        ''').lstrip()

        data = yaml.load(io.StringIO(content))

        tzinfo = datetime.timezone(offset=datetime.timedelta(hours=1))

        self.assertEqual(
            {
                'start': datetime.datetime(2022, 4, 1, 12, 4, 12, tzinfo=tzinfo),
                'end': datetime.datetime(2022, 4, 1, 12, 5, 37, tzinfo=tzinfo),
            },
            dict(data),
            "Should have parsed timezone aware times",
        )

        data['end'] += datetime.timedelta(hours=1)
        expected = textwrap.dedent('''
            start: 2022-04-01 12:04:12+01:00
            end: 2022-04-01 13:05:37+01:00
        ''').lstrip()

        output = io.StringIO()
        yaml.dump(data, output)

        self.assertEqual(
            expected,
            output.getvalue(),
            "Timestamps with timezones should be updated suitably",
        )
