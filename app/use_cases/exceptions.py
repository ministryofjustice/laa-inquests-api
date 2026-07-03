class ApplicationNotFoundError(Exception):
    pass


class CoronersLetterUploadError(Exception):
    pass


class CoronersLetterVirusDetectedError(CoronersLetterUploadError):
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
