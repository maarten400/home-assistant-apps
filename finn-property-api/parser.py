import json
import math
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse


class ParseError(ValueError):
    pass


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []
        self.documents = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.active = attrs.get("type") == "application/ld+json" or attrs.get("id") == "__NEXT_DATA__"
            self.parts = []

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            try:
                self.documents.append(json.loads("".join(self.parts)))
            except ValueError:
                pass
            self.active = False


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def number(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("Missing numeric value")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite value")
    return result


def parse_properties(html):
    scripts = Scripts()
    scripts.feed(html)
    records = {}
    candidates = set()
    explicit_empty = False
    for document in scripts.documents:
        for obj in walk(document):
            if obj.get("@type") == "ItemList" and obj.get("numberOfItems") == 0:
                explicit_empty = True
            raw_url = obj.get("canonical_url") or obj.get("url")
            if not isinstance(raw_url, str):
                continue
            url = urljoin("https://www.finn.no", raw_url)
            parsed = urlparse(url)
            if parsed.hostname not in {"www.finn.no", "finn.no"} or parsed.path != "/realestate/homes/ad.html":
                continue
            code = parse_qs(parsed.query).get("finnkode", [None])[0]
            if not code or not code.isdigit():
                continue
            candidates.add(code)
            try:
                geo = obj.get("geo") or obj.get("coordinates") or obj.get("location") or {}
                offers = obj.get("offers") or {}
                price = obj.get("price_nok", obj.get("price", offers.get("price")))
                if isinstance(price, dict):
                    price = price.get("amount", price.get("value"))
                lat = number(obj.get("latitude", geo.get("latitude", geo.get("lat"))))
                lon = number(obj.get("longitude", geo.get("longitude", geo.get("lon"))))
                price = number(price)
                title = obj.get("title") or obj.get("heading") or obj.get("name")
                if price <= 0 or not -90 <= lat <= 90 or not -180 <= lon <= 180 or not isinstance(title, str) or not title.strip():
                    continue
                records[code] = dict(id=code, title=title.strip(), url=url, price_nok=price, latitude=lat, longitude=lon)
            except (ValueError, TypeError, AttributeError):
                continue
    if candidates - records.keys():
        raise ParseError("Some listing candidates lack required fields; refusing partial results")
    if not records:
        if explicit_empty:
            return []
        raise ParseError("No complete properties recognized; live FINN markup may require a new adapter")
    return list(records.values())
