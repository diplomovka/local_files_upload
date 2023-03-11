from .file_data import FileData
from typing import List

class FileDataList:
    def __init__(self, files: List[FileData]):
        self.files = files

    def to_dict(self):
        return {"files": [file.to_dict() for file in self.files]}