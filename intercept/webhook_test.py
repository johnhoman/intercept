import base64
import json

import fastapi
from fastapi import FastAPI
from fastapi.testclient import TestClient
from kubernetes.client import V1Pod, V1Container

from intercept.webhook import mutating_webhook, MutatingWebhook


def get_patch(patch: str):
    decoded = base64.b64decode(patch).decode()
    return json.loads(decoded)


admission_review = {
    "kind": "AdmissionReview",
    "apiVersion": "admission.k8s.io/v1beta1",
    "request": {
        "uid": "0df28fbd-5f5f-11e8-bc74-36e6bb280816",
        "kind": {
            "group": "",
            "version": "v1",
            "kind": "Pod"
        },
        "resource": {
            "group": "",
            "version": "v1",
            "resource": "pods"
        },
        "namespace": "dummy",
        "operation": "CREATE",
        "userInfo": {
            "username": "system:serviceaccount:kube-system:replicaset-controller",
            "uid": "a7e0ab33-5f29-11e8-8a3c-36e6bb280816",
            "groups": [
                "system:serviceaccounts",
                "system:serviceaccounts:kube-system",
                "system:authenticated"
            ]
        },
        "object": {
            "metadata": {
                "generateName": "nginx-deployment-6c54bd5869-",
                "labels": {
                    "app": "nginx",
                    "pod-template-hash": "2710681425"
                },
                "annotations": {
                    "openshift.io/scc": "restricted"
                },
                "ownerReferences": [
                    {
                        "apiVersion": "extensions/v1beta1",
                        "kind": "ReplicaSet",
                        "name": "nginx-deployment-6c54bd5869",
                        "uid": "16c2b355-5f5d-11e8-ac91-36e6bb280816",
                        "controller": True,
                        "blockOwnerDeletion": True
                    }
                ]
            },
            "spec": {
                "volumes": [
                    {
                        "name": "default-token-tq5lq",
                        "secret": {
                            "secretName": "default-token-tq5lq"
                        }
                    }
                ],
                "containers": [
                    {
                        "name": "nginx",
                        "image": "nginx:1.7.9",
                        "ports": [
                            {
                                "containerPort": 80,
                                "protocol": "TCP"
                            }
                        ],
                        "resources": {},
                        "volumeMounts": [
                            {
                                "name": "default-token-tq5lq",
                                "readOnly": True,
                                "mountPath": "/var/run/secrets/kubernetes.io/serviceaccount"
                            }
                        ],
                        "terminationMessagePath": "/dev/termination-log",
                        "terminationMessagePolicy": "File",
                        "imagePullPolicy": "IfNotPresent",
                        "securityContext": {
                            "capabilities": {
                                "drop": [
                                    "KILL",
                                    "MKNOD",
                                    "SETGID",
                                    "SETUID"
                                ]
                            },
                            "runAsUser": 1000080000
                        }
                    }
                ],
                "restartPolicy": "Always",
                "terminationGracePeriodSeconds": 30,
                "dnsPolicy": "ClusterFirst",
                "serviceAccountName": "default",
                "serviceAccount": "default",
                "securityContext": {
                    "seLinuxOptions": {
                        "level": "s0:c9,c4"
                    },
                    "fsGroup": 1000080000
                },
                "imagePullSecrets": [
                    {
                        "name": "default-dockercfg-kksdv"
                    }
                ],
                "schedulerName": "default-scheduler"
            },
            "status": {}
        },
        "oldObject": None
    }
}

app = FastAPI()


@app.post("/mutate")
@mutating_webhook(V1Pod)
def add_init(pod):
    pod.spec.init_containers = [V1Container(command="ls -lart", name="list-dir")]


client = TestClient(app)


def test_add_init_container():

    response = client.post("/mutate", json=admission_review).json()
    patch = get_patch(response["response"]["patch"])
    assert patch[0]["op"] == "add"
    assert patch[0]["path"] == "/spec/initContainers"
    assert patch[0]["value"] == [{"command": "ls -lart", "name": "list-dir"}]


def test_add_init_container_again():
    def add_init_container(pod):
        pod.spec.init_containers = [V1Container(command="ls -lart", name="list-dir")]

    a = fastapi.FastAPI()

    webhook = MutatingWebhook(app=a)
    path = webhook.register(V1Pod, add_init_container)
    c = TestClient(a)
    response = c.post(path, json=admission_review).json().get("response")
    assert response["allowed"] is True
    patch = get_patch(response["patch"])
    assert patch[0]["op"] == "add"
    assert patch[0]["path"] == "/spec/initContainers"
    assert patch[0]["value"] == [{"command": "ls -lart", "name": "list-dir"}]
