import json
import unittest
from parser import ParseError, parse_properties


def html(value):
    return '<script type="application/ld+json">' + json.dumps(value) + '</script>'


class ParserTests(unittest.TestCase):
    def test_property(self):
        item = {"url": "https://www.finn.no/realestate/homes/ad.html?finnkode=123", "name": "Synthetic fixture", "offers": {"price": 4500000}, "geo": {"latitude": 60.2, "longitude": 5.3}}
        self.assertEqual(parse_properties(html(item))[0]["id"], "123")

    def test_partial_results_fail(self):
        complete = {"url": "/realestate/homes/ad.html?finnkode=123", "name": "Synthetic", "price": 100, "geo": {"latitude": 60, "longitude": 5}}
        incomplete = {"url": "/realestate/homes/ad.html?finnkode=456"}
        with self.assertRaises(ParseError):
            parse_properties(html([complete, incomplete]))

    def test_explicit_empty(self):
        self.assertEqual(parse_properties(html({"@type": "ItemList", "numberOfItems": 0})), [])

    def test_unknown_page_fails(self):
        with self.assertRaises(ParseError):
            parse_properties("<html>Access denied</html>")

    def test_missing_coordinates_fails(self):
        with self.assertRaises(ParseError):
            parse_properties(html({"url": "/realestate/homes/ad.html?finnkode=123", "name": "Synthetic fixture", "price": 100}))


if __name__ == "__main__":
    unittest.main()
