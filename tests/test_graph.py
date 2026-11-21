import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from src.graph import build_graph, print_tree, read_test_repository
from src.versions import matches, version_key


class GraphTests(unittest.TestCase):
    def test_depth_and_cycles(self):
        repo = read_test_repository(
            Path(__file__).resolve().parents[1] / "examples/repository.json"
        )
        self.assertEqual(build_graph("A", repo.__getitem__, 0), {"A": []})
        graph = build_graph("H", repo.__getitem__, 3)
        self.assertEqual(graph["E"], ["F"])
        self.assertEqual(graph["F"], ["B"])
        self.assertEqual(graph["D"], ["D"])
        output = io.StringIO()
        with redirect_stdout(output):
            print_tree("H", graph, 3)
        self.assertEqual(output.getvalue().splitlines(), [
            "H",
            "|-- A",
            "|   |-- B",
            "|   |   `-- E",
            "|   |-- C",
            "|   |   `-- E",
            "|   `-- D",
            "|       `-- D [cycle]",
            "`-- E",
            "    `-- F",
            "        `-- B",
        ])
        with redirect_stdout(output):
            print_tree("A", build_graph("A", repo.__getitem__, 4), 4)
        self.assertIn("B [cycle]", output.getvalue())

    def test_versions(self):
        self.assertTrue(matches("0.4.18", "^0.4.16"))
        self.assertFalse(matches("0.5.0", "^0.4.16"))
        self.assertTrue(matches("1.2.8", ">=1.2, <1.3"))
        self.assertTrue(matches("1.2.8", "1.2.*"))
        self.assertFalse(matches("1.3.0", "~1.2"))
        self.assertFalse(matches("1.2.3-beta.2", "^1.2"))
        self.assertTrue(matches("1.2.3-beta.2", "^1.2.3-beta.1"))
        self.assertLess(
            version_key("1.2.3-beta.2"), version_key("1.2.3-beta.10")
        )

    def test_comparison_requirements(self):
        cases = [
            ("1.9.0", ">1", False),
            ("1.9.0", ">=1", True),
            ("1.2.9", "<=1.2", True),
            ("1.2.0", "<1.2", False),
            ("1.2.3", "=1.2.3", True),
            ("1.2.4", "=1.2.3", False),
            ("1.3.0", ">1.2.3", True),
            ("1.2.3", "<=1.2.3", True),
        ]
        for version, requirement, expected in cases:
            with self.subTest(version=version, requirement=requirement):
                self.assertEqual(matches(version, requirement), expected)
