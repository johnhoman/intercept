import json
import typing
from functools import partial

from kubernetes.client import ApiClient

from intercept.types import Object, AdmissionReview
from intercept.responses import patch, allowed, denied


class Denied(Exception):
    pass


class _Req(object):
    def __init__(self, data):
        self.data = json.dumps(data)


def _deserialize(obj, type_):
    return ApiClient().deserialize(_Req(obj), type_)


def _serialize(obj):
    return ApiClient().sanitize_for_serialization(obj)


def mutating(type_):
    def outer(defaulter: typing.Callable[[Object], dict]):
        def inner(admission_review: AdmissionReview):
            obj = _deserialize(admission_review.request.object, type_)
            out = _serialize(defaulter(obj) or obj)
            return patch(admission_review, out)
        return inner
    return outer


OPERATION_CREATE = "CREATE"
OPERATION_UPDATE = "UPDATE"
OPERATION_DELETE = "DELETE"


def is_op(admission_review: AdmissionReview, op):
    admit_op = admission_review.request.operation
    return admit_op == op


is_create = partial(is_op, op=OPERATION_CREATE)
is_update = partial(is_op, op=OPERATION_UPDATE)
is_delete = partial(is_op, op=OPERATION_DELETE)


def validate_create(type_):
    def outer(validator: typing.Callable[[Object], dict]):
        def inner(admission_review: AdmissionReview):
            if is_create(admission_review):
                obj = _deserialize(admission_review.request.object, type_)
                try:
                    validator(obj)
                except Denied as err:
                    return denied(admission_review, str(err))
                return allowed(admission_review)
            else:
                return allowed(admission_review)

        return inner
    return outer


def validate_update(type_):
    def outer(validator: typing.Callable[[Object, Object], dict]):
        def inner(admission_review: AdmissionReview):
            if is_update(admission_review):

                obj = _deserialize(admission_review.request.object, type_)
                old = _deserialize(admission_review.request.old_object, type_)

                try:
                    validator(obj, old)
                except Denied as err:
                    return denied(admission_review, str(err))
                return allowed(admission_review)

            else:
                return allowed(admission_review)

        return inner
    return outer


def validate_delete(type_):
    def outer(validator: typing.Callable[[Object], dict]):
        def inner(admission_review: AdmissionReview):
            if is_create(admission_review):
                obj = _deserialize(admission_review.request.old_object, type_)
                try:
                    validator(obj)
                except Denied as err:
                    return denied(admission_review, str(err))
                return allowed(admission_review)
            else:
                return allowed(admission_review)

        return inner
    return outer
