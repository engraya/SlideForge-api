from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str = "1.0.0"


class ErrorDetail(BaseModel):
    error_code: str
    detail: str
    request_id: Optional[str] = None
