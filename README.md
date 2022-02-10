# intercept

## Example - Mutating Webhook
```python
from fastapi import FastAPI
from kubernetes.client import V1Pod, V1ServiceAccount
from intercept import mutating


app = FastAPI()


@app.post("/mutate-disable-istio-v1-pod")
@mutating(V1Pod)
def disable_istio(pod): 
    if pod.metadata.annotations is None:
        pod.metadata.annotations = {}
    pod.metadata.annotations["sidecar.istio.io/inject"] = "false"
    return pod


@app.post("/mutate-default-iam-role")
@mutating(V1ServiceAccount)
def set_iam_role(service_account):
    if service_account.metadata.annotations is None:
        service_account.metadata.annotations = {}
    service_account.metadata.annotations.setdefault(
        "eks.amazonaws.com/role-arn",
        "arn:aws:iam::0123456789010:role/spark-executor",
    )
    return service_account
```