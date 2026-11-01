"""Offline request and CLI regressions for the standalone OCR skills.

Run with: python -m unittest discover -s tests -v
"""

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("glmocr", "glmocr-formula", "glmocr-table", "glmocr-handwriting")


class OcrPageRangesTest(unittest.TestCase):
    def load_skill(self, name):
        path = ROOT / "skills" / name / "scripts" / "glm_ocr_cli.py"
        spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def response(*args, **kwargs):
        """Model only the documented optional, inclusive page selection."""
        payload = kwargs["json"]
        first = payload.get("start_page_id", 1)
        last = payload.get("end_page_id", 5)
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(
            {"md_results": "\n".join(f"page {n}" for n in range(first, last + 1))}
        ).encode()
        return response

    def test_cli_does_not_select_a_two_page_preview(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                module = self.load_skill(name)
                stdout = io.StringIO()
                with (
                    patch.dict(os.environ, {"ZHIPU_API_KEY": "offline-test-key"}),
                    patch.object(
                        module.requests, "post", side_effect=self.response
                    ) as post,
                    patch(
                        "sys.argv",
                        [
                            "glm_ocr_cli.py",
                            "--file-url",
                            "https://example.com/paper.pdf",
                        ],
                    ),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as exited,
                ):
                    module.main()
                self.assertEqual(exited.exception.code, 0)
                result = json.loads(stdout.getvalue())
                self.assertTrue(result["ok"])
                self.assertIn("page 5", result["text"])
                payload = post.call_args.kwargs["json"]
                self.assertNotIn("start_page_id", payload)
                self.assertNotIn("end_page_id", payload)

    def test_explicit_ranges_are_preserved_without_inventing_other_bound(self):
        for name in SKILLS:
            for options in (
                {"start_page_id": 3},
                {"end_page_id": 4},
                {"start_page_id": 2, "end_page_id": 4},
            ):
                with self.subTest(skill=name, options=options):
                    module = self.load_skill(name)
                    with (
                        patch.dict(os.environ, {"ZHIPU_API_KEY": "offline-test-key"}),
                        patch.object(
                            module.requests, "post", side_effect=self.response
                        ) as post,
                    ):
                        result = module.extract_text(
                            "https://example.com/paper.pdf", **options
                        )
                    self.assertTrue(result["ok"])
                    payload = post.call_args.kwargs["json"]
                    actual = {
                        key: payload[key]
                        for key in ("start_page_id", "end_page_id")
                        if key in payload
                    }
                    self.assertEqual(actual, options)

    def test_none_bounds_and_local_images(self):
        for name in SKILLS:
            with self.subTest(skill=name), tempfile.TemporaryDirectory() as directory:
                image = Path(directory) / "equation.png"
                image.write_bytes(b"\x89PNG\r\n\x1a\n")
                module = self.load_skill(name)
                with (
                    patch.dict(os.environ, {"ZHIPU_API_KEY": "offline-test-key"}),
                    patch.object(
                        module.requests, "post", side_effect=self.response
                    ) as post,
                ):
                    result = module.extract_text(
                        str(image), start_page_id=None, end_page_id=None
                    )
                self.assertTrue(result["ok"])
                payload = post.call_args.kwargs["json"]
                self.assertTrue(payload["file"].startswith("data:image/png;base64,"))
                self.assertEqual(payload["model"], "glm-ocr")
                self.assertNotIn("start_page_id", payload)
                self.assertNotIn("end_page_id", payload)


if __name__ == "__main__":
    unittest.main()
