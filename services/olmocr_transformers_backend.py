"""
Hugging Face Transformers ile olmOCR modeli (vLLM / olmocr CLI olmadan).

Resmi ornek: olmocr repo + allenai/olmOCR-2-7B-1025-FP8, processor Qwen2.5-VL-Instruct.
"""
from __future__ import annotations

import base64
import os
import subprocess
from io import BytesIO
from pathlib import Path

from olmocr.data.renderpdf import render_pdf_to_base64png
from olmocr.prompts import build_no_anchoring_v4_yaml_prompt
from PIL import Image

_model = None
_processor = None


def _pdf_page_count(path: Path) -> int:
    r = subprocess.run(
        ["pdfinfo", str(path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if r.returncode != 0:
        raise RuntimeError(f"pdfinfo basarisiz: {(r.stderr or r.stdout).strip()}")
    for line in r.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError("pdfinfo ciktisinda Pages yok")


def _image_file_to_base64_png(path: Path) -> str:
    with Image.open(path) as img:
        rgb = img.convert("RGB")
        buf = BytesIO()
        rgb.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _get_model_and_processor():
    global _model, _processor
    if _model is not None and _processor is not None:
        return _model, _processor

    import torch
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    model_id = os.getenv("OLMOCR_MODEL_ID", "allenai/olmOCR-2-7B-1025-FP8")
    processor_id = os.getenv("OLMOCR_PROCESSOR_ID", "Qwen/Qwen2.5-VL-7B-Instruct")

    kwargs = {"device_map": "auto"}
    dtype_name = os.getenv("OLMOCR_TORCH_DTYPE", "").strip()
    if dtype_name:
        kwargs["torch_dtype"] = getattr(torch, dtype_name)

    _model = Qwen2_5_VLForConditionalGeneration.from_pretrained(model_id, **kwargs).eval()
    _processor = AutoProcessor.from_pretrained(processor_id)
    return _model, _processor


def _resolve_device(model) -> str:
    try:
        dev = next(model.parameters()).device
        return str(dev)
    except StopIteration:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"


def _generate_from_base64_png(image_b64: str) -> str:
    import torch

    model, processor = _get_model_and_processor()
    device_s = _resolve_device(model)

    prompt_text = build_no_anchoring_v4_yaml_prompt()
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ],
        }
    ]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    main_image = Image.open(BytesIO(base64.b64decode(image_b64)))
    inputs = processor(text=[text], images=[main_image], padding=True, return_tensors="pt")

    target = torch.device(device_s) if device_s.startswith("cuda") else torch.device("cpu")
    inputs = {k: v.to(target) for k, v in inputs.items()}

    max_new = int(os.getenv("OLMOCR_MAX_NEW_TOKENS", "8192"))
    temperature = float(os.getenv("OLMOCR_TEMPERATURE", "0.1"))

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            temperature=temperature,
            max_new_tokens=max_new,
            num_return_sequences=1,
            do_sample=temperature > 0,
        )

    prompt_length = inputs["input_ids"].shape[1]
    new_tokens = output[:, prompt_length:]
    return processor.tokenizer.batch_decode(new_tokens, skip_special_tokens=True)[0].strip()


def run_olmocr_transformers_on_file(local_path: Path) -> str:
    """
    PDF: tum sayfalari sirayla isler, metinleri birlestirir.
    PNG/JPEG/WEBP: tek goruntu.
    """
    suf = local_path.suffix.lower()
    dim = int(os.getenv("OLMOCR_RENDER_LONGEST_DIM", "1288"))

    if suf == ".pdf":
        n = _pdf_page_count(local_path)
        parts = []
        for p in range(1, n + 1):
            b64 = render_pdf_to_base64png(str(local_path), p, target_longest_image_dim=dim)
            parts.append(_generate_from_base64_png(b64))
        return "\n\n".join(parts).strip()

    if suf in {".png", ".jpg", ".jpeg", ".webp"}:
        b64 = _image_file_to_base64_png(local_path)
        return _generate_from_base64_png(b64)

    raise RuntimeError(f"Transformers backend icin desteklenmeyen uzanti: {suf}")
