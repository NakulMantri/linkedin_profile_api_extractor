import unittest
from backend.scraper import extract_username

class TestLinkedInURLParsing(unittest.TestCase):
    def test_valid_urls(self):
        valid_urls = [
            ("https://www.linkedin.com/in/john-doe/", "john-doe"),
            ("https://www.linkedin.com/in/john-doe", "john-doe"),
            ("http://linkedin.com/in/john-doe-12345/", "john-doe-12345"),
            ("https://in.linkedin.com/in/john-doe?miniProfileUrn=urn%3Ali%3Afs_miniProfile%3A123", "john-doe"),
            ("https://uk.linkedin.com/in/john-doe#experience", "john-doe"),
        ]
        for url, expected in valid_urls:
            with self.subTest(url=url):
                self.assertEqual(extract_username(url), expected)

    def test_invalid_urls(self):
        invalid_urls = [
            "https://www.linkedin.com/feed/",
            "https://www.google.com",
            "https://linkedin.com/company/google",
            "not-a-url",
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    extract_username(url)

if __name__ == "__main__":
    unittest.main()
