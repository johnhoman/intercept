import typing
from typing import List

from pydantic import BaseModel, Field


class GroupVersionKind(BaseModel):
    group: str
    version: str
    kind: str


class GroupVersionResource(BaseModel):
    group: str
    version: str
    resource: str


class UserInfo(BaseModel):
    username: str
    uid: str
    groups: List[str]


class AdmissionRequest(BaseModel):
    uid: str
    kind: GroupVersionKind
    resource: GroupVersionResource
    namespace: str
    operation: str
    user_info: UserInfo = Field(..., alias="userInfo")
    object: dict
    old_object: dict = Field(None, alias="oldObject")


class AdmissionResponse(BaseModel):
    uid: str
    allowed: bool
    status: dict = None
    patch: str = None
    patch_type: str = Field("JSONPatch", alias="patchType")
    warnings: typing.List[str] = None


class AdmissionReview(BaseModel):
    kind: str
    api_version: str = Field(..., alias="apiVersion")
    request: AdmissionRequest
    response: AdmissionResponse = None


class Object(typing.Protocol):
    def to_dict(self) -> dict:
        ...

