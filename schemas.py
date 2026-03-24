from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class S3Ref(BaseModel):
    bucket: str
    prefix: str
    region: Optional[str] = None


class BatchRef(BaseModel):
    size: int = Field(default=10, ge=1, le=100)
    index: int = Field(default=0, ge=0)


class CallbackRef(BaseModel):
    url: str
    token: Optional[str] = None


class OcrJobInput(BaseModel):
    operation: Literal["submit_ocr_job"]
    documentId: str
    s3: Optional[S3Ref] = None
    sourceUrl: Optional[str] = None
    lang: str = "tur+eng"
    batch: BatchRef = Field(default_factory=BatchRef)
    callback: Optional[CallbackRef] = None


class OcrPage(BaseModel):
    pageNo: int
    text: str


class OcrJobOutput(BaseModel):
    ok: bool
    documentId: str
    pages: List[OcrPage]
    provider: str = "olmocr"
    elapsedMs: int
