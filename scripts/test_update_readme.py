import unittest

from update_readme import markdown, replace_section


class UpdateReadmeTest(unittest.TestCase):
    def test_replace_section_updates_only_marked_content(self) -> None:
        content = "before\n<!-- TEST_START -->\nold\n<!-- TEST_END -->\nafter\n"

        updated = replace_section(content, "TEST", "new")

        self.assertEqual(
            updated,
            "before\n<!-- TEST_START -->\nnew\n<!-- TEST_END -->\nafter\n",
        )

    def test_replace_section_requires_one_marker_pair(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "exactly one TEST marker pair"):
            replace_section("no markers", "TEST", "new")

    def test_markdown_distinguishes_contributions_and_capped_commits(self) -> None:
        items = [
            {
                "kind": "repository",
                "name": "project",
                "url": "https://example.com/project",
                "count": 100,
                "count_is_lower_bound": True,
                "release": None,
                "time": "2026-08-19T00:00:00Z",
            },
            {
                "kind": "contribution",
                "name": "org/repo",
                "url": "https://example.com/org/repo",
                "count": 2,
                "time": "2026-08-18T00:00:00Z",
            },
        ]

        result = markdown(items)

        self.assertIn("[project](https://example.com/project) (100+ commits)", result)
        self.assertIn("[org/repo](https://example.com/org/repo) (2 merged PRs)", result)


if __name__ == "__main__":
    unittest.main()
