class AutoContinuerError(RuntimeError):
    """Expected operational error with a useful user-facing message."""


class ConfigurationError(AutoContinuerError):
    pass


class CodexCommandError(AutoContinuerError):
    pass


class ProtocolError(AutoContinuerError):
    pass


class TransportError(AutoContinuerError):
    pass
