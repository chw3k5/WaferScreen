class ResProcessingError(Exception):
    """The base class for exceptions the occur during resonator processing."""
    pass


class ResMinIsLeftMost(ResProcessingError):
    """Raised when the RWHM definition detects that the resonator's minima is the left-most point"""
    pass


class ResMinIsRightMost(ResProcessingError):
    """Raised when the RWHM definition detects that the resonator's minima is the right-most point"""
    pass
