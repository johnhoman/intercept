from intercept.webhook import Manager, GVK
from intercept.webhook import subresource
from intercept.webhook import set_defaults
from kubernetes.client import V1Pod, V1EnvVar, V1Container


webhook = Manager()


@webhook.defaulting.pod(labels=dict(foo="bar"))
@subresource("spec", "containers", 0)
@set_defaults(env=list)
def add_env_var_1(container: V1Container):
    container.env.append(V1EnvVar(name="USER", value="jhoman"))


@webhook.defaulting(resource=GVK("", "v1", "Pod"), labels=dict(foo="bar"))
@subresource("spec", "containers", 0)
def add_env_var_2(container: V1Container):
    container.env.append(V1EnvVar(name="TMP", value="/tmp"))


# @webhook.defaulting(resource=GVK("", "v1", "ServiceAccount"), labels=dict(foo="bar"))
# @subresource("metadata", "annotations")
# def add_annotation(annotations: dict):
#     from fastapi.logger import logger
#     logger.warning(annotations)
#     annotations["key"] = "value"


@webhook.defaulting.pod(labels=dict(foo="bar"))
def add_env_var_3(pod: V1Pod):
    pod.spec.containers[0].env.append(V1EnvVar(
        name="USERNAME", value="bhoman"
    ))


if __name__ == "__main__":
    webhook.start()
