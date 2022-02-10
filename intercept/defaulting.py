import copy
import typing

from intercept.webhook import mutating
from intercept import types, responses


def pod(defaulter: typing.Callable[[types.Object], typing.Optional[types.Object]]):
    from kubernetes.client import V1Pod
    return mutating(V1Pod)(defaulter)


def container0(defaulter: typing.Callable[[types.Object], typing.Optional[types.Object]]):
    from kubernetes.client import V1Pod

    def _defaulter(p: typing.Union[types.Object, V1Pod]) -> typing.Optional[types.Object]:
        container = p.spec.containers[0]
        out = defaulter(container) or container
        p.spec.containers[0] = out
        return p

    return pod(_defaulter)


def set_annotation(name: str):
    """
    :param name:
    :return:

    Examples
    --------
    @app.post("/mutate-set-annotation")
    @defaulting.set_annotation(name="istio.something.io/something")
    def set_something() -> str:
        return "something"
    """

    def outer(setter: typing.Callable[[], str]):
        def inner(admission_review: types.AdmissionReview) -> dict:
            obj = copy.deepcopy(admission_review.request.object)
            metadata = obj["metadata"]
            annotations = metadata.setdefault("annotations", {})
            annotations[name] = setter()
            metadata["annotations"] = annotations
            obj["metadata"] = metadata
            return responses.patch(admission_review, obj)
        return inner
    return outer