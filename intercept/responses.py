import base64

import jsonpatch

from intercept.types import AdmissionResponse, AdmissionReview, Object


def patch(admission_review: AdmissionReview, obj: dict) -> AdmissionResponse:
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
    return admission_review.dict(by_alias=True, exclude_unset=True)
