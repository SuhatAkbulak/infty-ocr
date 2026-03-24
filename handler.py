import runpod
from typing import Any, Dict
from schemas import OcrJobInput
from services.ocr_pipeline import process_ocr_job


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        payload = event.get("input", {})
        job = OcrJobInput.model_validate(payload)
        out = process_ocr_job(job)
        return out.model_dump()
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
