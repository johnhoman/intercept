import json
import typing

import fastapi
from kubernetes.client import ApiClient
from kubernetes.client import (
    V1MutatingWebhookConfiguration,
    V1MutatingWebhook,
    AdmissionregistrationV1WebhookClientConfig,
    AdmissionregistrationV1ServiceReference,
)

from intercept.types import Object, AdmissionReview
from intercept.responses import patch


class _Req(object):
    def __init__(self, data):
        self.data = json.dumps(data)


def mutating_webhook(type_):
    def outer(defaulter: typing.Callable[[Object], Object]):
        def inner(admission_review: AdmissionReview):

            obj = ApiClient().deserialize(
                _Req(admission_review.request.object),
                type_,
            )
            out = ApiClient().sanitize_for_serialization(defaulter(obj) or obj)
            return patch(admission_review, out)
        return inner
    return outer


class MutatingWebhook(object):

    def __init__(self, app=None):
        self._app = app or fastapi.FastAPI()

    def register(self, type_, function, options=None):
        type_name = type_.__name__
        func_name = function.__name__.replace("_", "-")
        path = f"/mutate-{type_name}-{func_name}"
        self._app.post(path, response_model=AdmissionReview)(
            mutating_webhook(type_)(function)
        )

        return path
