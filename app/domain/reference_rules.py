import base64
import re
import string

AMBIGUOUS_CHARACTERS = "B8G6I10OQDS5Z2"


class ReferenceRules:
    """Shared rules for generated references: the character set that is allowed
    and the banned words that must never appear. Reused by every reference
    generator so the rules stay identical across resources."""

    def __init__(
        self,
        banned_words: list[str],
        ambiguous_characters: str = AMBIGUOUS_CHARACTERS,
    ) -> None:
        self.ambiguous_characters = ambiguous_characters
        self.allowed_characters = [
            c
            for c in string.ascii_uppercase + string.digits
            if c not in ambiguous_characters
        ]
        self.banned_words = [
            word.upper()
            for word in banned_words
            if re.match(
                rf"^(?:Q[^{ambiguous_characters}]{{0,8}}|[^{ambiguous_characters}]{{1,9}})$",
                word.upper(),
            )
        ]
        self.banned_words_pattern = re.compile(
            pattern=r"(?:"
            + "|".join(re.escape(word) for word in self.banned_words)
            + ")"
        )

    def contains_banned_word(self, text: str) -> bool:
        if not self.banned_words:
            return False
        return bool(self.banned_words_pattern.search(text))

    @classmethod
    def from_file(cls, file_path: str) -> "ReferenceRules":
        with open(file_path, "r") as banned_word_file:
            banned_words = [
                base64.b64decode(line.strip()).decode("utf-8")
                for line in banned_word_file
                if line.strip()  # Skip empty lines
            ]
        return cls(banned_words)
