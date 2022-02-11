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
    username: typing.Optional[str]
    uid: typing.Optional[str]
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

    class Config:
        allow_population_by_field_name = True


class AdmissionResponse(BaseModel):
    uid: str
    allowed: bool
    status: dict = None
    patch: str = None
    patch_type: str = Field(None, alias="patchType")
    warnings: typing.List[str] = None

    class Config:
        allow_population_by_field_name = True


class AdmissionReview(BaseModel):
    kind: str
    api_version: str = Field(..., alias="apiVersion")
    request: AdmissionRequest
    response: AdmissionResponse = None

    class Config:
        allow_population_by_field_name = True


class Object(typing.Protocol):
    def to_dict(self) -> dict:
        ...

