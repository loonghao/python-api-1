# -*- coding: utf-8 -*-
"""
module author: Long Hao <hoolongvfx@gmail.com>
"""


class RayVisionError(Exception):
    """Base for all RayVision API Errors"""
    pass


class RayVisionFileDownloadError(RayVisionError):
    """Exception for file download-related errors"""
    pass


class RayVisionArgsError(RayVisionError):
    pass


class Fault(RayVisionError):
    """Exception when server side exception detected."""
    pass


class AuthenticationFault(Fault):
    """Exception when the server side reports an error related to authentication"""
    pass


class MissingTwoFactorAuthenticationFault(Fault):
    """Exception when the server side reports an error related to missing
    two factor authentication credentials
    """
    pass
