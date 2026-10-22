class ApplicationNotFoundError(Exception):
    pass


class ApplicationNotGrantedError(Exception):
    pass


class SentryRedactableError(Exception):
    """Message may embed a file name/SDS key; pass `safe_message` without it so
    Sentry can show useful context instead of fully redacting the message.
    Without `safe_message`, the message is treated as unsafe and fully redacted."""

    def __init__(self, message: str = "", safe_message: str | None = None) -> None:
        super().__init__(message)
        self.safe_message = safe_message

    @classmethod
    def safe(cls, message: str) -> "SentryRedactableError":
        """Use when `message` has no sensitive content and can be reported to
        Sentry verbatim."""
        return cls(message, safe_message=message)


class CoronersLetterUploadError(SentryRedactableError):
    pass


class CoronersLetterVirusCheckError(CoronersLetterUploadError):
    pass


class CoronersLetterVirusDetectedError(SentryRedactableError):
    pass


class ClaimEvidenceUploadError(SentryRedactableError):
    pass


class ClaimEvidenceVirusCheckError(ClaimEvidenceUploadError):
    pass


class ClaimEvidenceVirusDetectedError(SentryRedactableError):
    pass


class CoronersLetterNotFoundError(SentryRedactableError):
    pass


class CoronersLetterRetrievalError(SentryRedactableError):
    pass


class InvalidCoronersLetterDocumentIdError(SentryRedactableError):
    pass


class CoronersLetterDeleteError(SentryRedactableError):
    pass


class SDSLetterRetrievalError(SentryRedactableError):
    pass


class ClaimEvidenceNotFoundError(SentryRedactableError):
    pass


class ClaimNotFoundError(Exception):
    pass


class ClaimAssessmentConflictError(Exception):
    pass


class ClaimEvidenceRetrievalError(SentryRedactableError):
    pass


class ClaimEvidenceDeleteError(SentryRedactableError):
    pass


class InvalidClaimEvidenceDocumentIdError(SentryRedactableError):
    pass


class InvalidDateRangeError(Exception):
    pass


class SDSClaimEvidenceRetrievalError(SentryRedactableError):
    pass


class ProviderDetailsRetrievalError(Exception):
    pass


class ProviderOfficeMismatchError(Exception):
    pass


class ReportGenerationError(Exception):
    pass


class AuditError(Exception):
    pass


class GrantDecisionError(Exception):
    pass


class RefuseDecisionError(Exception):
    pass


class InvalidClaimError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
