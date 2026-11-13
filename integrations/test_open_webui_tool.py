import base64
from html.parser import HTMLParser
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from integrations.open_webui_tool import Tools


class IframeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.src = None

    def handle_starttag(self, tag, attrs):
        if tag == "iframe":
            self.src = dict(attrs).get("src")


class OpenWebUIToolTests(unittest.TestCase):
    def setUp(self):
        self.tool = Tools()

    def response_text(self, response):
        self.assertEqual(response.headers["content-disposition"], "inline")
        return response.body.decode("utf-8")

    def state_from_response(self, response):
        parser = IframeParser()
        parser.feed(self.response_text(response))
        parts = urlsplit(parser.src)
        encoded = parse_qs(parts.fragment)["state"][0]
        return parts, json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))

    def test_mermaid_unicode_hash_round_trip_and_query(self):
        self.tool.valves.studio_url = "https://example.test/studio?lang=en&state=old"
        source = 'graph LR\n A["Réception 📦"] --> B["検査"]'
        parts, state = self.state_from_response(self.tool.render_vsm(source, "Département"))
        self.assertEqual(state, {"title": "Département", "mermaid": source})
        self.assertEqual(parse_qs(parts.query), {"lang": ["en"]})
        self.assertTrue(parts.fragment.startswith("state="))
        self.assertIn("allowfullscreen", self.response_text(self.tool.render_vsm(source)))

    def test_full_project_round_trip(self):
        state = {"project": {"title": "Existing"}, "mermaid": "graph LR\n A-->B",
                 "metrics": {"A": {"ct": 3}}, "positions": {"A": {"x": 1, "y": 2}}}
        _, decoded = self.state_from_response(self.tool.open_vsm_studio(json.dumps(state)))
        self.assertEqual(decoded, state)

    def test_metadata_schema_round_trip_and_compact_edges(self):
        state = {
            "schemaVersion": 1,
            "title": "Hydrated map",
            "mermaid": "graph LR\n P1[\"Process\"] --> P2[\"Customer\"]",
            "nodes": {"P1": {"icon": "process_dedicated", "category": "process"},
                      "P2": {"icon": "customer", "category": "people"}},
            "metrics": {"P1": {"ct": 4}, "P2": {"icon": "customer"}},
            "edges": {"P1_to_P2": {"flowType": "callout", "label": "Reference"}},
            "notes": {"note_1": {"targetId": "P1", "text": "Check the work instruction"}},
            "styles": {"P1": {"fill": "#123456"}},
        }
        _, decoded = self.state_from_response(self.tool.open_vsm_studio(json.dumps(state)))
        self.assertEqual(decoded, state)

    def test_metadata_schema_survives_post_message_delivery(self):
        self.tool.valves.max_url_chars = 1
        state = {
            "schemaVersion": 1,
            "mermaid": "graph LR\n A-->B",
            "nodes": {"A": {"icon": "data_box", "category": "information"}},
            "edges": {"A_to_B": {"flowType": "information-electronic"}},
            "notes": {"note_1": {"targetId": "A", "text": "UTF-8 ✓"}},
        }
        body = self.response_text(self.tool.open_vsm_studio(json.dumps(state)))
        encoded_state = body.split("var s=", 1)[1].split(",url=", 1)[0]
        self.assertEqual(json.loads(encoded_state), state)

    def test_invalid_inputs_report_errors(self):
        for value in ("not json", "[]", '{"mermaid": 12}', '{"mermaid": ""}'):
            with self.subTest(value=value):
                self.assertIn("Invalid VSM JSON:", self.response_text(self.tool.open_vsm_studio(value)))
        self.assertIn("non-empty", self.response_text(self.tool.render_vsm(" ")))
        self.assertIn("Title must be a string", self.response_text(self.tool.render_vsm("graph LR", None)))

    def test_invalid_metadata_is_reported(self):
        for state in (
            {"mermaid": "graph LR\n A-->B", "nodes": {"A": {"icon": "not-an-icon"}}},
            {"mermaid": "graph LR\n A-->B", "nodes": {"A": {"category": "unknown"}}},
            {"mermaid": "graph LR\n A-->B", "edges": {"A_to_B": {"flowType": "unknown"}}},
            {"mermaid": "graph LR\n A-->B", "edges": {"A_to_B": {"index": -1}}},
            {"schemaVersion": 2, "mermaid": "graph LR\n A-->B"},
        ):
            with self.subTest(state=state):
                response = self.tool.open_vsm_studio(json.dumps(state))
                self.assertIn("Invalid VSM JSON:", self.response_text(response))

    def test_invalid_urls_report_errors(self):
        for url in ("javascript:alert(1)", "https://user:pass@example.test/", "https://example.test/#other",
                    "https://example.test:invalid/"):
            with self.subTest(url=url):
                self.tool.valves.studio_url = url
                self.assertIn("Invalid Studio URL:", self.response_text(self.tool.render_vsm("graph LR")))

    def test_large_state_handshake_and_script_escaping(self):
        self.tool.valves.max_url_chars = 1
        self.tool.valves.studio_url = "https://example.test/studio?x=%3Cscript%3E"
        source = 'graph LR\n A["</script><script>alert(1)</script>"]'
        body = self.response_text(self.tool.render_vsm(source))
        self.assertNotIn(source, body)
        self.assertNotIn("</script><script>alert", body)
        self.assertIn("\\u003c/script\\u003e", body)
        self.assertIn("e.source!==f.contentWindow", body)
        self.assertIn("e.origin!==origin", body)
        self.assertIn("e.origin==='null'?'*':origin", body)
        self.assertIn("vsm:ready", body)
        self.assertIn("vsm:loaded", body)
        self.assertIn("vsm:error", body)
        self.assertIn("f.src=url", body)
        self.assertIn("iframe:height", body)
        parser = IframeParser()
        parser.feed(body)
        self.assertIsNone(parser.src)

    def test_html_attribute_escaping(self):
        self.tool.valves.studio_url = 'https://example.test/studio?x="quoted"'
        body = self.response_text(self.tool.render_vsm("graph LR"))
        self.assertNotIn('x="quoted"', body)
        parser = IframeParser()
        parser.feed(body)
        self.assertEqual(parse_qs(urlsplit(parser.src).query)["x"], ['"quoted"'])


if __name__ == "__main__":
    unittest.main()
