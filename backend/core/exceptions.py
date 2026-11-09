from rest_framework import status
from rest_framework.exceptions import APIException


class ConflictError(APIException):
    """409: permintaan valid, tetapi bertentangan dengan status objek saat ini."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state of the resource."
    default_code = "conflict"