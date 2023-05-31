"""Custom exceptions."""
import tornado.web

from common.config import config
from common.lib.plugins import get_plugin_by_name

log = config.get_logger("cloudumi")
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()


class BaseException(Exception):
    def __init__(self, msg: str = "") -> None:
        self.msg = msg
        log.error(msg)  # use your logging things here
        stats.count(
            self.__class__.__name__,
            tags={
                "msg": msg,
                "parent_exceptions": [
                    str(base.__name__) for base in self.__class__.__bases__
                ],
            },
        )
        super().__init__(msg)

    def __str__(self):
        """Stringifies the message."""
        return self.msg


class CognitoJWTException(BaseException):
    """Raised when something went wrong in token verification proccess"""


class WebAuthNError(tornado.web.HTTPError):
    """Authentication Error"""

    def __init__(self, **kwargs):
        kwargs["status_code"] = 401
        super().__init__(**kwargs)


class ProvisionedThroughputExceededError(Exception):
    pass


class MissingDataException(BaseException):
    """MissingDataException."""

    pass


class InvalidCertificateException(BaseException):
    """InvalidCertificateException."""

    pass


class MissingCertificateException(BaseException):
    """MissingCertificateException."""

    pass


class NoUserException(BaseException):
    """NoUserException."""

    pass


class NoGroupsException(BaseException):
    """NoGroupsException."""

    pass


class PendingRequestAlreadyExists(BaseException):
    """Pending request already exists for user."""

    pass


class NoExistingRequest(BaseException):
    """No existing request exists for user."""

    pass


class CertTooOldException(BaseException):
    """MTLS Certificate is too old, despite being valid."""

    pass


class NotAMemberException(BaseException):
    """User is not a member of a group they are being removed from."""

    pass


class NoCredentialSubjectException(BaseException):
    """Unable to find credential subject for domain."""

    pass


class BackgroundCheckNotPassedException(BaseException):
    """User does not have a background check where one is required."""

    pass


class DifferentUserGroupDomainException(BaseException):
    """Users cannot be added to groups that are under different domains."""

    pass


class UserAlreadyAMemberOfGroupException(BaseException):
    """Unable to add a user to a group that they're already a member of."""

    pass


class UnableToModifyRestrictedGroupMembers(BaseException):
    """Unable to add/remove a user to a group that is marked as restricted."""

    pass


class UnableToEditSensitiveAttributes(BaseException):
    """Unable edit sensitive attributes."""

    pass


class NoMatchingRequest(BaseException):
    """Cannot find a matching request"""

    pass


class BulkAddPrevented(BaseException):
    """Bulk adding user to group is prevented"""

    pass


class UnauthorizedToAccess(BaseException):
    """Unauthorized to access resource"""

    pass


class NoRoleTemplateException(BaseException):
    """The IAM role template for the per-user role does not exist."""

    pass


class UserRoleLambdaException(BaseException):
    """The Lambda function to create IAM roles errored out for some reason."""

    pass


class PolicyUnchanged(BaseException):
    """Updated policy is identical to existing policy."""

    pass


class InvalidDomainError(BaseException):
    """Invalid domain"""

    pass


class UnableToGenerateRoleName(BaseException):
    """Unable to generate role name within constraints (64 characters, up to 10 duplicate usernames handled"""

    pass


class InvalidInvocationArgument(BaseException):
    """Function was invoked with an invalid argument."""

    pass


class UserRoleNotAssumableYet(BaseException):
    """Newly created user role is not assumable yet."""

    pass


class RoleTrustPolicyModified(BaseException):
    """Role trust policy was modified to allow request. Retry in a bit."""

    pass


class NoArnException(BaseException):
    """No ARN passed to endpoint."""

    pass


class MustBeFte(BaseException):
    """Only Full Time Employees are allowed"""

    pass


class Unauthorized(BaseException):
    """Unauthorized"""

    pass


class InvalidRequest(BaseException):
    """Invalid Request Parameter passed to function"""

    pass


class InvalidRequestParameter(BaseException):
    """Invalid Request Parameter passed to function"""

    pass


class MissingRequestParameter(BaseException):
    """Missing Request Parameter passed to function"""

    pass


class KriegerError(BaseException):
    """Krieger communication error"""

    pass


class BaseWebpackLoaderException(BaseException):
    """
    Base exception for django-webpack-loader.
    """

    pass


class WebpackError(BaseWebpackLoaderException):
    """
    General webpack loader error.
    """

    pass


class WebpackLoaderBadStatsError(BaseWebpackLoaderException):
    """
    The stats file does not contain valid data.
    """

    pass


class WebpackLoaderTimeoutError(BaseWebpackLoaderException):
    """
    The bundle took too long to compile.
    """

    pass


class WebpackBundleLookupError(BaseWebpackLoaderException):
    """
    The bundle name was invalid.
    """

    pass


class UnsupportedRedisDataType(BaseException):
    """Unsupported Redis Data Type passed"""

    pass


class DataNotRetrievable(BaseException):
    """Data was expected but is not retrievable"""

    pass


class MissingConfigurationValue(BaseException):
    """Unable to find expected configuration value"""

    pass


class ExpiredData(BaseException):
    """Data was retrieved but is older than expected"""

    pass


class UnsupportedChangeType(BaseException):
    """Unsupported Change Type"""

    pass


class ResourceNotFound(BaseException):
    """Resource Not Found"""

    pass


class UnableToAuthenticate(BaseException):
    """Unable to authenticate user or app"""

    pass


class TenantNoCentralRoleConfigured(BaseException):
    """
    Tenant has no central role configured
    """

    pass


class WorkOSNoOrganizationId(BaseException):
    """
    Tenant does not have an Organization ID in WorkOS
    """

    pass


class NoMatchingTenant(BaseException):
    """
    A matching tenant was not found
    """

    pass
