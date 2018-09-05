# -*- coding: utf-8 -*-
"""
module author: Long Hao <hoolongvfx@gmail.com>
"""


class RayVisionError(Exception):
    """Base for all RayVision RayVisionAPI Errors"""
    pass


class RayVisionFileDownloadError(RayVisionError):
    """Exception for file download-related errors"""
    pass


class RayVisionArgsError(RayVisionError):
    pass


class AuthenticationFault(RayVisionError):
    """Exception when the server side reports an error related to authentication"""
    pass


class MissingTwoFactorAuthenticationFault(RayVisionError):
    """Exception when the server side reports an error related to missing
    two factor authentication credentials
    """
    pass

# Error list.
ERROR_FEEDBACK = {
    "download task failure: at least one file is failure": "download task failure",
    "upload task failure: at least one file is failure": "upload task failure"
}
