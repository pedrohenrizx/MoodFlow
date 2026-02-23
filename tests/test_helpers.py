import unittest

from app import friendly_name


class FriendlyNameTests(unittest.TestCase):
    def test_uses_name_when_present(self):
        self.assertEqual(friendly_name("Ana", "ana@example.com"), "Ana")

    def test_falls_back_to_email_local_part(self):
        self.assertEqual(friendly_name("", "ana@example.com"), "ana")

    def test_handles_missing_values(self):
        self.assertEqual(friendly_name("", ""), "")


if __name__ == "__main__":
    unittest.main()
