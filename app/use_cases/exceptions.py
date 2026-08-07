class ApplicationNotFoundError(Exception):
    pass


class ApplicationNotGrantedError(Exception):
    pass


class CoronersLetterUploadError(Exception):
    pass


class CoronersLetterVirusCheckError(CoronersLetterUploadError):
    pass


class CoronersLetterVirusDetectedError(Exception):
    pass


class ClaimEvidenceUploadError(Exception):
    pass


class ClaimEvidenceVirusCheckError(ClaimEvidenceUploadError):
    pass


class ClaimEvidenceVirusDetectedError(Exception):
    pass


class CoronersLetterNotFoundError(Exception):
    pass


class CoronersLetterRetrievalError(Exception):
    pass


class InvalidCoronersLetterDocumentIdError(Exception):
    pass


class SDSLetterRetrievalError(Exception):
    pass


class ClaimEvidenceNotFoundError(Exception):
    pass


class ClaimEvidenceRetrievalError(Exception):
    pass


class ClaimEvidenceDeleteError(Exception):
    pass


class InvalidClaimEvidenceDocumentIdError(Exception):
    pass


class SDSClaimEvidenceRetrievalError(Exception):
    pass


class ProviderDetailsRetrievalError(Exception):
    pass


class ReportGenerationError(Exception):
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
