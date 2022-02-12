import copy
import inspect
import json
from functools import partial, singledispatch
import os
import typing
import uuid

import uvicorn
import fastapi
from kubernetes.client import (
    AdmissionregistrationV1Api,
    AdmissionregistrationV1ServiceReference,
    AdmissionregistrationV1WebhookClientConfig,
    ApiClient,
    V1LabelSelector,
    V1MutatingWebhook,
    V1RuleWithOperations,
    V1MutatingWebhookConfiguration,
)

from intercept.models import Object, AdmissionReview
from intercept.responses import patch, allowed, denied

from kubernetes.client import (
    V1Pod,
    V1ServiceAccount,
    V1Service,
)


@singledispatch
def scheme(type_):
    pass


def _gvk(*args):
    def inner(_):
        return GroupVersionKind(*args)
    return inner


scheme.register(V1Pod)(_gvk("", "v1", "Pod"))
scheme.register(V1ServiceAccount)(_gvk("", "v1", "ServiceAccount"))
scheme.register(V1Service)(_gvk("", "v1", "Service"))


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


def _do(func, obj: dict) -> dict:
    sig = inspect.signature(func)
    parameters = list(sig.parameters.values())
    parameter = parameters.pop()
    if parameter.annotation and hasattr(parameter.annotation, "openapi_types"):
        obj = _deserialize(obj, parameter.annotation)
        obj = _serialize(func(obj) or obj)
    else:
        obj = func(obj) or obj
    return obj


class GroupVersionKind:

    def __init__(self, group, version, kind):
        self._group = group
        self._version = version
        self._kind = kind

    def __repr__(self):
        return f"GroupVersionKind('{self._group}', '{self._version}', '{self._kind}')"

    def __str__(self):
        group = self._group
        if group == "":
            group = "core"
        group = group.replace(".", "-")
        return f"{group}-{self._version}-{self._kind}".lower()

    def __eq__(self, other):
        return self.kind == other.kind and self.group == other.group and self.version == other.version

    def __hash__(self):
        return hash(str(self))

    @property
    def kind(self):
        return self._kind

    @property
    def group(self):
        return self._group

    @property
    def version(self):
        return self._version


GVK = GroupVersionKind


class _Defaulting:

    def __init__(self):
        self._registry = {}

    def __call__(self, *, labels: dict = None, resource: GroupVersionKind = None):
        def inner(defaulter: typing.Callable[[Object], dict]):
            key = json.dumps(labels, sort_keys=True)
            shared_labels = self._registry.setdefault(key, {})
            defaulters = shared_labels.setdefault(resource, [])
            defaulters.append(defaulter)
        return inner

    def pod(self, labels: dict = None) -> typing.Callable:
        return self(labels=labels, resource=GroupVersionKind("", "v1", "Pod"))

    def service_account(self, labels: dict = None) -> typing.Callable:
        return self(labels=labels, resource=GroupVersionKind("", "v1", "ServiceAccount"))

    def register(self, app, client_config: AdmissionregistrationV1WebhookClientConfig = None):

        webhooks = []
        # TODO: labels will collide
        for k, (key, types) in enumerate(self._registry.items()):
            for gvk, defaulters in types.items():
                uid = str(uuid.uuid4())[:8]
                path = f"/mutate-{gvk}-{uid}"

                client_config = copy.deepcopy(client_config)
                client_config.service.path = path

                webhook = V1MutatingWebhook(
                    client_config=client_config,
                    name=f"intercept.mutate.{gvk}-{uid}".lower(),
                    object_selector=V1LabelSelector(
                        match_labels=json.loads(key),
                    ),
                    admission_review_versions=["v1"],
                    side_effects="None",
                    rules=[
                        V1RuleWithOperations(
                            api_groups=[gvk.group],
                            api_versions=[gvk.version],
                            resources=[gvk.kind.lower() + "s"],
                            operations=[OPERATION_CREATE, OPERATION_UPDATE]
                        ),
                    ]
                )
                webhooks.append(webhook)

                @app.post(path)
                def review(admission_review: AdmissionReview):
                    obj = admission_review.request.object
                    for defaulter in defaulters:
                        if obj["kind"] == gvk.kind:
                            obj = _do(defaulter, obj)
                    return patch(admission_review, obj)

        return webhooks


class Manager:

    def __init__(self, app=None):
        self._app = app or fastapi.FastAPI()
        self._defaulting = _Defaulting()

    @property
    def defaulting(self):
        return self._defaulting

    def manifest(self):
        pass

    def start(self):
        tmpdir = os.getenv("$TMP", "/tmp")
        cert_dir = os.path.join(tmpdir, "serving-certs")

        service_name = os.getenv("SERVICE_NAME")
        service_namespace = os.getenv("SERVICE_NAMESPACE")

        from kubernetes.config import load_incluster_config
        load_incluster_config()

        with open(os.path.join(cert_dir, "ca.crt"), mode="rb") as open_file:
            import base64
            ca_bundle = base64.b64encode(open_file.read()).decode()

        client_config = AdmissionregistrationV1WebhookClientConfig(
            ca_bundle=ca_bundle,
            service=AdmissionregistrationV1ServiceReference(
                name=service_name,
                namespace=service_namespace,
                port=80,
            )
        )

        webhook_config = V1MutatingWebhookConfiguration(
            metadata={
                "name": f"{service_name}-{service_namespace}",
            },
            webhooks=self._defaulting.register(self._app, client_config=client_config),
        )

        api = AdmissionregistrationV1Api()
        api.create_mutating_webhook_configuration(webhook_config)

        uvicorn.run(
            self._app,
            host="0.0.0.0",
            port=8888,
            log_level="info",
            ssl_certfile=os.path.join(cert_dir, "tls.crt"),
            ssl_keyfile=os.path.join(cert_dir, "tls.key"),
        )
        api.delete_mutating_webhook_configuration(webhook_config.metadata["name"])
