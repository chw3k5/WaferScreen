class ResProcessingError(Exception):
    """The base class for exceptions the occur during resonator processing."""
    pass


class ResMinIsLeftMost(ResProcessingError):
    """Raised when the RWHM definition detects that the resonator's minima is the left-most point"""
    pass


class ResMinIsRightMost(ResProcessingError):
    """Raised when the RWHM definition detects that the resonator's minima is the right-most point"""
    pass


class FailedResFit(ResProcessingError):
    """Raised when the curvefit has a runtime error and a the resonator fit fails to converge"""
    pass


# Lambda processing
class LambdaProcessingError(Exception):
    """The base class for exceptions the occur during lambda curve fitting and processing."""
    pass


class NoDataForCurveFit(LambdaProcessingError):
    """Empty lists, [], were return for currentuA and/or freqGHz needed for lambda fitting"""
    pass


class NotEnoughDataForCurveFit(LambdaProcessingError):
    """Curve Fit for lambda fitting has more free parameters then data points"""
    pass


class OptimalParametersNotFoundForCurveFit(LambdaProcessingError):
    """Optimal parameters not found: Number of calls to function has reached maxfev"""
    pass
