

class UnicornException(Exception):
    def __init__(self, name: str):
        self.name = name


class OwnerError(Exception):
    pass

