import base64

import jsonpatch

from intercept.types import AdmissionResponse, AdmissionReview, Object


def _response(admission_review: AdmissionReview) -> dict:
    return admission_review.dict(by_alias=True, exclude_unset=True)


def patch(admission_review: AdmissionReview, obj: dict) -> dict:
    """
    :param admission_review:
    :param original:
    :param obj:
    :return:
    """

    p = jsonpatch.JsonPatch.from_diff(admission_review.request.object, obj)
    response = AdmissionResponse(
        allowed=True,
        uid=admission_review.request.uid,
        patch=base64.b64encode(str(p).encode()).decode()
    )
    admission_review.response = response
    return _response(admission_review)


def allowed(admission_review) -> dict:
    admission_review.response = AdmissionResponse(
        allowed=True,
        uid=admission_review.request.uid,
    )
    return _response(admission_review)


def denied(admission_review, reason="") -> dict:
    admission_review.response = AdmissionResponse(
        allowed=False,
        uid=admission_review.request.uid,
        status={"message": reason, "code": 403}
    )
    return _response(admission_review)
