class UrlBaseException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class CacheException(UrlBaseException):
    def __init__(self, message):
        self.message = message
        super().__init__(str(self))

    def __str__(self):
        return f"CACHE: {self.message}"

# Cache Exceptions
class CacheKeyNotFoundException(CacheException):
    def __init__(self, key):
        super().__init__(f"Key {key} not found in cache")

class CacheKeyAlreadyExistsException(CacheException):
    def __init__(self, key):
        super().__init__(f"Key {key} already exists in cache")
