from abc import ABC, abstractmethod


class PdfGenerationPort(ABC):
    @abstractmethod
    def generate_pdf(self, template_name: str, context: dict) -> bytes: ...
