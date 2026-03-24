"""GPU ve runpod SDK gerektirmez: OLMOCR_MOCK=true ile pipeline."""

import os
import unittest

from pydantic import ValidationError


class TestPipelineMock(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["OLMOCR_MOCK"] = "true"

    def test_process_ocr_source_url_mock(self) -> None:
        from schemas import OcrJobInput
        from services.ocr_pipeline import process_ocr_job

        job = OcrJobInput(
            operation="submit_ocr_job",
            documentId="sha256:smoke",
            sourceUrl="https://example.com/sample.pdf",
            lang="tur+eng",
        )
        out = process_ocr_job(job)
        self.assertTrue(out.ok)
        self.assertEqual(out.documentId, "sha256:smoke")
        self.assertEqual(out.provider, "olmocr-transformers")
        self.assertEqual(len(out.pages), 1)
        self.assertIn("[mock-olmocr]", out.pages[0].text)
        self.assertEqual(out.pages[0].pageNo, 1)

    def test_schema_rejects_missing_operation(self) -> None:
        from schemas import OcrJobInput

        with self.assertRaises(ValidationError):
            OcrJobInput.model_validate(
                {"documentId": "x", "sourceUrl": "https://example.com/a.pdf"}
            )


if __name__ == "__main__":
    unittest.main()
