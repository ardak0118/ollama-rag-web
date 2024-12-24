import re
from typing import List, Optional, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter

def remove_empty_lines(text: str) -> str:
    lines = text.splitlines()
    non_empty_lines = (line for line in lines if line.strip())
    return "\n".join(non_empty_lines)

class MarkdownTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(
        self,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        is_separator_regex: bool = True,
        is_remove_empty_line: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(keep_separator=keep_separator, **kwargs)
        self._separators = separators or [
            r"\n\n",
            r"\n",
            r"。|！|？",
            r"\.\s|\!\s|\?\s",
            r"；|;\s",
            r"，|,\s"
        ]
        self._is_separator_regex = is_separator_regex
        self._is_remove_empty_line = is_remove_empty_line