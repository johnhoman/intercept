import json
import typing

from kubernetes.client import ApiClient

from intercept.types import Object, AdmissionReview
from intercept.responses import patch, allowed, denied


class Denied(Exception):
    pass


class _Req(object):
    def __init__(self, data):
        self.data = json.dumps(data)


def mutating(type_):
    def outer(defaulter: typing.Callable[[Object], dict]):
        def inner(admission_review: AdmissionReview):

            obj = ApiClient().deserialize(
                _Req(admission_review.request.object),
                type_,
            )
            out = ApiClient().sanitize_for_serialization(defaulter(obj) or obj)
            return patch(admission_review, out)
        return inner
    return outer


OPERATION_CREATE = "CREATE"
OPERATION_UPDATE = "UPDATE"
OPERATION_DELETE = "DELETE"


def validate_create(type_):
    def outer(validator: typing.Callable[[Object], dict]):
        def inner(admission_review: AdmissionReview):
            admit_op = admission_review.request.operation
            if admit_op != OPERATION_CREATE:
                return allowed(admission_review)

            obj = ApiClient().deserialize(
                _Req(admission_review.request.object),
                type_,
            )

            try:
                validator(obj)
            except Denied as err:
                return denied(admission_review, str(err))
            return allowed(admission_review)

        return inner
    return outer


def validate_update(type_):
    def outer(validator: typing.Callable[[Object, Object], dict]):
        def inner(admission_review: AdmissionReview):
            admit_op = admission_review.request.operation
            if admit_op != OPERATION_CREATE:
                return allowed(admission_review)

            obj = ApiClient().deserialize(
                _Req(admission_review.request.object),
                type_,
            )
            old = ApiClient().deserialize(
                _Req(admission_review.request.old_object),
                type_,
            )

            try:
                validator(obj, old)
            except Denied as err:
                return denied(admission_review, str(err))
            return allowed(admission_review)

        return inner
    return outer

