"""No network or paid API is needed for these tests."""
import json
import unittest
from unittest.mock import patch

from creative_agent.ai_provider import (
    ENDPOINT, GenerationError, GenerationSettings, build_messages,
    generate, generate_campaign, validate_generated_content,
)
from creative_agent.planner import Brief


def response(module, *, usage=True):
    from creative_agent.ai_provider import FIELDS
    content = {key: f"Draft {key} [VERIFY]" for key in FIELDS[module]}
    outer = {"choices": [{"message": {"content": json.dumps(content)}}]}
    if usage:
        outer["usage"] = {"prompt_tokens": 38, "completion_tokens": 29}
    return json.dumps(outer).encode()


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.brief = Brief("Demo", "new designers", "education", "instagram", "portfolios")
        self.settings = GenerationSettings(model="example-model", max_output_tokens=200)

    def test_strict_schema_rejects_extra_and_missing_fields(self):
        with self.assertRaises(GenerationError):
            validate_generated_content("copywriting", {"headline": "Only"})
        with self.assertRaises(GenerationError):
            validate_generated_content("copywriting", {"headline": "a", "caption": "b", "cta": "c", "secret": "x"})

    def test_schema_rejects_empty_and_nonstring(self):
        with self.assertRaises(GenerationError):
            validate_generated_content("copywriting", {"headline": "", "caption": "OK", "cta": "OK"})
        with self.assertRaises(GenerationError):
            validate_generated_content("copywriting", {"headline": 2, "caption": "OK", "cta": "OK"})

    def test_explicit_api_key_required(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            with self.assertRaises(GenerationError):
                generate(self.brief, "copywriting", settings=self.settings)

    def test_bad_budget_configuration(self):
        with self.assertRaises(ValueError):
            GenerationSettings("model", max_estimated_request_usd=0.01)
        with self.assertRaises(ValueError):
            GenerationSettings("model", max_output_tokens=-1)

    def test_module_messages_are_structured(self):
        messages = build_messages(self.brief, "strategy")
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("requested_module", messages[1]["content"])

    def test_transport_and_usage_without_secret_leak(self):
        def fake(req, timeout):
            self.assertEqual(req.full_url, ENDPOINT)
            self.assertEqual(req.get_method(), "POST")
            self.assertIn("Bearer example-secret", req.get_header("Authorization"))
            return response("copywriting")
        output = generate(self.brief, "copywriting", settings=GenerationSettings(
            "example-model", estimated_input_usd_per_million=1,
            estimated_output_usd_per_million=2,
        ), api_key="example-secret", transport=fake)
        self.assertEqual(output["usage"]["input_tokens"], 38)
        self.assertAlmostEqual(output["usage"]["estimated_cost_usd"], 0.000096)
        self.assertFalse(output["publishable"])
        self.assertNotIn("example-secret", json.dumps(output))

    def test_preflight_budget_blocks_request(self):
        invoked = []
        def fake(req, timeout):
            invoked.append(1)
            return response("copywriting")
        with self.assertRaisesRegex(GenerationError, "estimated request cost"):
            generate(self.brief, "copywriting", settings=GenerationSettings(
                "example-model", estimated_input_usd_per_million=1000000,
                estimated_output_usd_per_million=1000000,
                max_estimated_request_usd=0.01,
            ), api_key="dummy", transport=fake)
        self.assertEqual(invoked, [])

    def test_bad_provider_response_fails_closed(self):
        with self.assertRaises(GenerationError):
            generate(self.brief, "copywriting", settings=self.settings,
                     api_key="dummy", transport=lambda req, timeout: b"not-json")

    def test_unknown_module_rejected(self):
        with self.assertRaises(ValueError):
            generate(self.brief, "unknown", settings=self.settings, api_key="dummy",
                     transport=lambda req, timeout: b"{}")

    def test_campaign_composes_three_drafts_without_approval(self):
        def fake(req, timeout):
            module = json.loads(req.data)["messages"][1]["content"]
            return response(json.loads(module)["requested_module"])
        output = generate_campaign(self.brief, settings=self.settings,
                                   api_key="dummy", transport=fake)
        self.assertEqual(set(output["generated"]), {"strategy", "copywriting", "video_script"})
        self.assertFalse(output["publishable"])
        self.assertEqual(output["review"]["state"], "needs_review")

    def test_missing_usage_is_not_invented(self):
        out = generate(self.brief, "strategy", settings=self.settings,
                       api_key="dummy", transport=lambda req, timeout: response("strategy", usage=False))
        self.assertIsNone(out["usage"]["input_tokens"])
        self.assertIsNone(out["usage"]["estimated_cost_usd"])

    def test_provider_http_error_does_not_expose_body(self):
        from io import BytesIO
        from urllib.error import HTTPError
        def fake(req, timeout):
            raise HTTPError(ENDPOINT, 401, "secret details", {}, BytesIO(b"secret-key"))
        with self.assertRaisesRegex(GenerationError, "HTTP error: 401") as ctx:
            generate(self.brief, "copywriting", settings=self.settings,
                     api_key="dummy", transport=fake)
        self.assertNotIn("secret-key", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
