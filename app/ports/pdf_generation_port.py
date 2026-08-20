from abc import ABC, abstractmethod

from app.models.application.certificate import ApplicationCertificate


class PdfGenerationPort(ABC):
    @abstractmethod
    def generate_pdf(
        self, template_name: str, context: ApplicationCertificate
    ) -> bytes: ...

    @abstractmethod
    def generate_print_letter_pdf(self, context: ApplicationCertificate) -> bytes: ...
