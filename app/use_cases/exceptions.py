class ApplicationNotFoundError(Exception):
    pass


class ApplicationNotGrantedError(Exception):
    pass


class CoronersLetterUploadError(Exception):
    pass


class CoronersLetterVirusDetectedError(Exception):
    pass


class ClaimEvidenceUploadError(Exception):
    pass


class ClaimEvidenceVirusDetectedError(Exception):
    pass


class ProceedingsNotFoundError(Exception):
    pass


class CoronersLetterNotFoundError(Exception):
    pass


class CoronersLetterRetrievalError(Exception):
    pass


class InvalidCoronersLetterDocumentIdError(Exception):
    pass


class SDSLetterRetrievalError(Exception):
    pass


class ProviderDetailsRetrievalError(Exception):
    pass


class InvalidClaimError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
