from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BilingualText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zh: str
    en: str


class PatchOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["replace", "reorder", "hide", "restore"]
    path: str
    supported_by: list[str] = Field(default_factory=list)
    reason: str = ""
    value: BilingualText | list[str] | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "PatchOperation":
        if self.op == "replace":
            if not isinstance(self.value, BilingualText):
                raise ValueError("replace 必须提供中英文 value")
            if not self.reason.strip() or not self.supported_by:
                raise ValueError("文本修改必须提供 reason 与 supported_by")
        elif self.op == "reorder":
            if not isinstance(self.value, list) or not self.value:
                raise ValueError("reorder 必须提供非空 ID 列表")
        elif self.value is not None:
            raise ValueError(f"{self.op} 不接受 value")
        return self


class ResumePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operations: list[PatchOperation] = Field(max_length=80)

