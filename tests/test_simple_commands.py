from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


class SimpleCommandsTests(unittest.TestCase):
    maxDiff = None

    # Any command which reads the compstate and displays information about it
    # should be listed here. Commands which modify the compstate should be
    # tested separately.
    SIMPLE_COMMANDS: list[tuple[str, ...]] = [
        ('awards',),
        ('knocked-out-teams',),
        ('match-order-teams',),
        ('show-league-table',),
        ('show-schedule',),
        ('summary',),
        ('top-match-points',),
        ('validate',),
        ('youtube-chapters', '600'),
    ]

    def test_command_snapshot(self) -> None:
        dummy_compstate = Path(__file__).parent / 'dummy'
        snapshots = Path(__file__).parent / 'snapshots'

        for command_parts in self.SIMPLE_COMMANDS:
            command, *args = command_parts

            with self.subTest(command=command, args=args):
                result = subprocess.run(
                    ['srcomp', command, str(dummy_compstate), *args],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                self.assertEqual(0, result.returncode, result.stdout.decode())

                snapshot = (snapshots / command).with_suffix('.txt')

                # To record a new snapshot, uncomment the following line and run the tests:
                # snapshot.write_bytes(result.stdout)

                expected = snapshot.read_bytes()
                self.assertEqual(
                    expected.decode(),
                    result.stdout.decode(),
                    "Command output unexpected content",
                )

    def test_commands_list(self) -> None:
        output = subprocess.check_output(['srcomp', 'list-commands'], text=True)
        commands = set(output.split())
        self.assertIn('list-commands', commands)

    def test_commands_are_documented(self) -> None:
        output = subprocess.check_output(['srcomp', 'list-commands'], text=True)
        commands = set(output.split())

        commands_docs_dir = Path(__file__).parent.parent / 'docs' / 'commands'
        documented_commands = set(x.stem for x in commands_docs_dir.glob('*.rst'))

        missing = commands - documented_commands
        extra = documented_commands - commands
        self.assertEqual(
            set(),
            missing,
            (
                "Commands are missing documentation "
                "(consider running `script/docs/create-command-docs.py`)"
            ),
        )
        self.assertEqual(
            set(),
            extra,
            "Documentation exists for non-existent commands",
        )
