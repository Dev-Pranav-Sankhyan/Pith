"""
Unit tests for Pith Automated LLM Ingestion Pipeline.
"""

import unittest
from core.llm import clean_json_response, get_llm_provider, SimulatedProvider
from pipeline.ingest_llm import run_pipeline


class TestLLMClient(unittest.TestCase):
    def test_clean_json_response(self):
        # Case 1: Markdown code block
        raw_1 = "```json\n{\"test\": 123}\n```"
        self.assertEqual(clean_json_response(raw_1), '{"test": 123}')

        # Case 2: Bare code fence
        raw_2 = "```\n{\"key\": \"val\"}\n```"
        self.assertEqual(clean_json_response(raw_2), '{"key": "val"}')

        # Case 3: Pure JSON without fences
        raw_3 = '{"already": "clean"}'
        self.assertEqual(clean_json_response(raw_3), '{"already": "clean"}')

    def test_provider_factory_dry_run(self):
        provider = get_llm_provider(dry_run=True)
        self.assertIsInstance(provider, SimulatedProvider)

    def test_unknown_provider_raises_error(self):
        with self.assertRaises(ValueError):
            get_llm_provider(provider_name="nonexistent_llm_engine")


class TestLLMPipelineRun(unittest.TestCase):
    def test_pipeline_dry_run_success(self):
        raw_text = (
            "The Linux Foundation and CNCF announced the creation of the Open Agent Protocol (OAP), "
            "a vendor-neutral standard for connecting AI models to external tools, databases, and enterprise software. "
            "Under the charter, working group members will establish open governance for Model Context Protocol "
            "and cross-platform agent execution specs."
        )
        metadata = {
            "title": "Open Agent Protocol Initiative Launch",
            "publisher": "Linux Foundation Press",
            "url": "https://www.linuxfoundation.org/press/open-agent-protocol"
        }

        result = run_pipeline(
            raw_text=raw_text,
            metadata=metadata,
            provider_name="simulated",
            dry_run=True,
            add_to_issue=False,
            rebuild=False
        )

        self.assertEqual(result["status"], "success")
        self.assertGreaterEqual(result["score"], 60.0)
        self.assertIn("card", result)
        card_data = result["card"]
        self.assertEqual(card_data["signal_level"], "High")
        self.assertIn("developer", card_data["role_views"])
        self.assertIn("founder", card_data["role_views"])
        self.assertIn("investor", card_data["role_views"])


if __name__ == "__main__":
    unittest.main()
