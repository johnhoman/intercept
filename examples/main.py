from http import HTTPStatus

from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from intercept import mutating, defaulting
from kubernetes.client import V1Pod, V1EnvVar


app = FastAPI()


@app.post("/mutate-add-env-var")
@defaulting.pod
def add_env_var(pod: V1Pod):
    pod.spec.containers[0].env = []
    pod.spec.containers[0].env.append(V1EnvVar(
        name="USER", value="jhoman"
    ))


@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    from fastapi.logger import logger
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    logger.error(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)


if __name__ == "__main__":
    import os
    from uvicorn import run
    tmpdir = os.getenv("$TMP", "/tmp")
    cert_dir = os.path.join(tmpdir, "serving-certs")
    run(
        app,
        host="0.0.0.0",
        port=8888,
        log_level="info",
        ssl_certfile=os.path.join(cert_dir, "tls.crt"),
        ssl_keyfile=os.path.join(cert_dir, "tls.key"),
    )