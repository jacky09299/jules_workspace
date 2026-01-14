from enum import Enum, auto

class DataType(Enum):
    ANY = auto()
    IMAGE = auto()      # PIL Image or numpy array representing image
    GRID = auto()       # 2D numpy array (0/1)
    PATH = auto()       # List of (x, y) tuples
    TEXT = auto()       # String
    JSON = auto()       # Dict or List
    NUMPY_ARRAY = auto() # General numpy array

class ValidationResult:
    def __init__(self, valid: bool, message: str = ""):
        self.valid = valid
        self.message = message

    @classmethod
    def success(cls):
        return cls(True)

    @classmethod
    def failure(cls, message):
        return cls(False, message)
