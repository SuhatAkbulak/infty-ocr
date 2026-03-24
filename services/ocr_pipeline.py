from time import perf_counter
from typing import List
import os
import shlex
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from schemas import OcrJobInput, OcrJobOutput, OcrPage
from services.s3_io import list_page_keys, download_s3_key
from services.url_io import download_source_url


def run_olmocr_local(image_path: Path, lang: str, timeout_ms: int, workspace_dir: Path) -> str:
    """
    olmOCR komutunu container icinde local calistirir.
    Varsayilan komut template:
      olmocr "{workspace}" --markdown --pdfs "{input}" --workers 1 --pages_per_group 1

    Ozellestirmek icin `OLMOCR_CMD_TEMPLATE` kullanilabilir.
    """
    template = os.getenv(
        "OLMOCR_CMD_TEMPLATE",
        'olmocr "{workspace}" --markdown --pdfs "{input}" --workers 1 --pages_per_group 1',
    )
    cmd = template.format(input=str(image_path), lang=lang, workspace=str(workspace_dir))
    proc = subprocess.run(
        shlex.split(cmd),
        capture_output=True,
        text=True,
        timeout=timeout_ms / 1000,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"olmOCR komutu basarisiz (code={proc.returncode}): {stderr}")

    # olmOCR genelde sonucu stdout yerine workspace/markdown altina yazar.
    md_dir = workspace_dir / "markdown"
    if md_dir.exists():
        md_files = sorted(md_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if md_files:
            content = md_files[0].read_text(encoding="utf-8", errors="replace").strip()
            if content:
                return content

    text = (proc.stdout or "").strip()
    if text:
        return text
    raise RuntimeError("olmOCR cikti uretmedi (ne markdown ne stdout).")


def process_ocr_job(job: OcrJobInput) -> OcrJobOutput:
    started = perf_counter()
    timeout_ms = int(os.getenv("OLMOCR_TIMEOUT_MS", "120000"))
    download_timeout_ms = int(os.getenv("OCR_DOWNLOAD_TIMEOUT_MS", "30000"))
    max_source_mb = int(os.getenv("OCR_MAX_SOURCE_MB", "50"))
    mock_mode = os.getenv("OLMOCR_MOCK", "true").strip().lower() in {"1", "true", "yes", "on"}

    start_idx = job.batch.index * job.batch.size

    pages: List[OcrPage] = []
    with TemporaryDirectory(prefix="infty-ocr-") as tmp_dir:
        tmp_root = Path(tmp_dir)

        if job.sourceUrl:
            if mock_mode:
                pages.append(OcrPage(pageNo=1, text=f"[mock-olmocr] document={job.documentId} source={job.sourceUrl}"))
            else:
                local_source = tmp_root / "source.bin"
                workspace = tmp_root / "workspace-source"
                workspace.mkdir(parents=True, exist_ok=True)
                source_kind = download_source_url(job.sourceUrl, local_source, download_timeout_ms, max_source_mb)
                local_input = local_source.with_suffix(f".{source_kind}")
                local_source.rename(local_input)
                text = run_olmocr_local(local_input, job.lang, timeout_ms, workspace)
                pages.append(OcrPage(pageNo=1, text=text))

            elapsed_ms = int((perf_counter() - started) * 1000)
            return OcrJobOutput(
                ok=True,
                documentId=job.documentId,
                pages=pages,
                provider="olmocr",
                elapsedMs=elapsed_ms,
            )

        if not job.s3:
            raise RuntimeError("s3 veya sourceUrl alanlarindan biri zorunlu.")

        selected_keys: List[str]
        if mock_mode:
            end_idx = start_idx + job.batch.size
            selected_keys = [f"{job.s3.prefix.rstrip('/')}/mock-page-{i + 1}.jpg" for i in range(start_idx, end_idx)]
        else:
            all_keys = list_page_keys(job.s3.bucket, job.s3.prefix, job.s3.region)
            end_idx = start_idx + job.batch.size
            selected_keys = all_keys[start_idx:end_idx]
            if not selected_keys:
                elapsed_ms = int((perf_counter() - started) * 1000)
                return OcrJobOutput(
                    ok=True,
                    documentId=job.documentId,
                    pages=[],
                    provider="olmocr",
                    elapsedMs=elapsed_ms,
                )

        for i, key in enumerate(selected_keys):
            page_no = start_idx + i + 1
            s3_uri = f"s3://{job.s3.bucket}/{key}"

            if mock_mode:
                text = f"[mock-olmocr] document={job.documentId} page={page_no} source={s3_uri}"
            else:
                file_name = Path(key).name or f"page-{page_no}.jpg"
                local_path = tmp_root / f"{page_no:05d}-{file_name}"
                page_workspace = tmp_root / f"workspace-{page_no:05d}"
                download_s3_key(job.s3.bucket, key, local_path, job.s3.region)
                page_workspace.mkdir(parents=True, exist_ok=True)
                text = run_olmocr_local(local_path, job.lang, timeout_ms, page_workspace)

            pages.append(OcrPage(pageNo=page_no, text=text))

    elapsed_ms = int((perf_counter() - started) * 1000)
    return OcrJobOutput(
        ok=True,
        documentId=job.documentId,
        pages=pages,
        provider="olmocr",
        elapsedMs=elapsed_ms,
    )
