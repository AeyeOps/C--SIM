"""
Pareto distribution functions.

Port of C++SIM Stat/Pareto.cc.
"""

from __future__ import annotations

import math
import sys


class Pareto:
    """
    Pareto distribution probability functions.

    The Pareto distribution is a power-law probability distribution
    commonly used in economics, actuarial science, and network modeling.

    Parameters:
        gamma: Shape parameter (γ > 0)
        k: Scale/minimum value parameter (k > 0)

    PDF: f(x) = γ * k^γ / x^(γ+1)  for x >= k
    CDF: F(x) = 1 - (k/x)^γ       for x >= k

    From Stat/src/Pareto.cc.
    """

    def __init__(self, gamma: float, k: float) -> None:
        """
        Initialize Pareto distribution.

        Args:
            gamma: Shape parameter (γ)
            k: Scale/minimum value (k)
        """
        self._gamma = gamma
        self._k = k
        self._k_to_gamma = math.pow(k, gamma)

    @property
    def gamma(self) -> float:
        """Shape parameter."""
        return self._gamma

    @property
    def k(self) -> float:
        """Scale/minimum value parameter."""
        return self._k

    def pdf(self, x: float) -> float:
        """
        Probability density function.

        Args:
            x: Value to evaluate (must be >= k)

        Returns:
            PDF value, or 0 if x < k (with warning)

        From Pareto.cc:49-59.
        """
        if x < self._k:
            print("Pareto::pdf - invalid value for x.", file=sys.stderr)
            return 0.0

        return self._k_to_gamma / math.pow(x, self._gamma + 1)

    def cdf(self, x: float) -> float:
        """
        Cumulative distribution function.

        Args:
            x: Value to evaluate (must be >= k)

        Returns:
            CDF value, or 0 if x < k (with warning)

        From Pareto.cc:61-71.
        """
        if x < self._k:
            print("Pareto::cdf - invalid value for x.", file=sys.stderr)
            return 0.0

        return 1.0 - math.pow(self._k / x, self._gamma)
