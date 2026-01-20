"""
Random number streams - exact port of C++SIM Random.n algorithms.

CRITICAL: These implementations must produce identical sequences to the C++
version for validation to pass. All algorithms verified against
Include/ClassLib/Random.n and Include/ClassLib/Random.h.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

# Constants from C++ implementation
TWO_26 = 67108864  # 2**26
M = 100000000
B = 31415821
M1 = 10000

# Default seeds (from Random.h:76)
DEFAULT_MG_SEED = 772531  # Must be odd
DEFAULT_LCG_SEED = 1878892440

# Module-level cache for initial series (optimization only - not for state sharing!)
# In C++, each stream constructs its own series independently. We cache the
# initial series values (computed from default seeds) to speed up initialization,
# but each stream gets its OWN copy and evolves independently.
_initial_series_cache: list[float] | None = None
_initial_mseed_after_series: int = 0  # mseed state after generating initial series
_initial_lseed: int = 0  # lseed is unchanged during series generation


def reset_prng_cache() -> None:
    """Reset the module-level PRNG cache. Call between simulation runs."""
    global _initial_series_cache, _initial_mseed_after_series, _initial_lseed
    _initial_series_cache = None
    _initial_mseed_after_series = 0
    _initial_lseed = 0


class RandomStream(ABC):
    """
    Abstract base class for random number streams.

    Implements the dual-generator approach from C++SIM:
    - Multiplicative generator (MGen) for shuffle table updates
    - Linear congruential generator with Maclaren-Marsaglia shuffle

    Algorithm sources:
    - MGen: Mitrani 1992, private correspondence
    - LCG: Sedgewick 1983, "Algorithms", pp. 36-38
    - Shuffle: Maclaren-Marsaglia (Knuth Vol 2)
    """

    def __init__(
        self,
        mg_seed: int = DEFAULT_MG_SEED,
        lcg_seed: int = DEFAULT_LCG_SEED,
    ) -> None:
        global _initial_series_cache, _initial_mseed_after_series, _initial_lseed

        # Seed cleanup: MGSeed must be odd and positive
        if mg_seed % 2 == 0:
            mg_seed -= 1
        if mg_seed < 0:
            mg_seed = -mg_seed
        if lcg_seed < 0:
            lcg_seed = -lcg_seed

        self._mseed = mg_seed
        self._lseed = lcg_seed

        is_default = mg_seed == DEFAULT_MG_SEED and lcg_seed == DEFAULT_LCG_SEED

        if is_default and _initial_series_cache is not None:
            # Use cached initial series values (each stream gets own COPY)
            # and the mseed state after series generation
            self._series = _initial_series_cache.copy()
            self._mseed = _initial_mseed_after_series
            # Note: _lseed stays at DEFAULT_LCG_SEED (unchanged during series init)
        else:
            # Initialize series with 128 MGen values
            self._series = [self._mgen() for _ in range(128)]

            if is_default:
                # Cache initial series for future instances
                _initial_series_cache = self._series.copy()
                _initial_mseed_after_series = self._mseed
                _initial_lseed = self._lseed

    def _mgen(self) -> float:
        """
        Multiplicative generator (Mitrani 1992).

        Y[i+1] = Y[i] * 5^5 mod 2^26
        Period: 2^24, initial seed must be odd.

        From Random.n:45-59.
        """
        # MSeed = (MSeed * 25) % TWO_26  (twice)
        # MSeed = (MSeed * 5) % TWO_26   (once)
        # This computes MSeed * 5^5 = MSeed * 3125
        self._mseed = (self._mseed * 25) % TWO_26
        self._mseed = (self._mseed * 25) % TWO_26
        self._mseed = (self._mseed * 5) % TWO_26
        return self._mseed / TWO_26

    def _uniform(self) -> float:
        """
        Linear congruential generator with Maclaren-Marsaglia shuffle.

        From Random.n:61-90.
        """
        # LCG step with overflow prevention
        p0 = self._lseed % M1
        p1 = self._lseed // M1
        q0 = B % M1
        q1 = B // M1

        self._lseed = (((((p0 * q1 + p1 * q0) % M1) * M1 + p0 * q0) % M) + 1) % M

        # Shuffle using MGen
        choose = self._lseed % 128  # series has 128 elements
        result = self._series[choose]
        self._series[choose] = self._mgen()

        return result

    def error(self) -> float:
        """
        Chi-square error measure on uniform distribution.

        From Random.n:92-104.
        """
        r = 100
        n = 100 * r
        f = [0] * r

        for _ in range(n):
            f[int(self._uniform() * r)] += 1

        t = sum(x * x for x in f)
        rt = r * t
        rtn = rt / n - n
        return 1.0 - (rtn / r)

    @abstractmethod
    def __call__(self) -> float:
        """Generate next random value from the distribution."""
        ...

    def copy_from(self, other: RandomStream) -> None:
        """Copy state from another stream."""
        self._mseed = other._mseed
        self._lseed = other._lseed
        self._series = other._series.copy()


class UniformStream(RandomStream):
    """
    Uniform distribution on [lo, hi].

    From Random.n:106-111.
    """

    def __init__(
        self,
        lo: float,
        hi: float,
        stream_select: int = 0,
        mg_seed: int = DEFAULT_MG_SEED,
        lcg_seed: int = DEFAULT_LCG_SEED,
    ) -> None:
        super().__init__(mg_seed, lcg_seed)
        self._lo = lo
        self._hi = hi
        self._range = hi - lo

        # Skip values for stream independence
        for _ in range(stream_select * 1000):
            self._uniform()

    def __call__(self) -> float:
        return self._lo + (self._range * self._uniform())


class Draw:
    """
    Boolean draw with probability p.

    Returns True with probability p, False with probability (1-p).
    Note: C++ returns (s() >= prob), so prob is P(False).

    From Random.n:113-118.
    """

    def __init__(
        self,
        p: float,
        stream_select: int = 0,
        mg_seed: int = DEFAULT_MG_SEED,
        lcg_seed: int = DEFAULT_LCG_SEED,
    ) -> None:
        self._s = UniformStream(0.0, 1.0, stream_select, mg_seed, lcg_seed)
        self._prob = p

    def __call__(self) -> bool:
        return self._s() >= self._prob


class ExponentialStream(RandomStream):
    """
    Exponential distribution with given mean.

    From Random.n:120-125.
    """

    def __init__(
        self,
        mean: float,
        stream_select: int = 0,
        mg_seed: int = DEFAULT_MG_SEED,
        lcg_seed: int = DEFAULT_LCG_SEED,
    ) -> None:
        super().__init__(mg_seed, lcg_seed)
        self._mean = mean

        for _ in range(stream_select * 1000):
            self._uniform()

    def __call__(self) -> float:
        return -self._mean * math.log(self._uniform())


class ErlangStream(RandomStream):
    """
    Erlang distribution with given mean and standard deviation.

    From Random.n:127-134.
    """

    def __init__(
        self,
        mean: float,
        std_dev: float,
        stream_select: int = 0,
        mg_seed: int = DEFAULT_MG_SEED,
        lcg_seed: int = DEFAULT_LCG_SEED,
    ) -> None:
        super().__init__(mg_seed, lcg_seed)
        self._mean = mean
        self._std_dev = std_dev
        # k = (mean/stddev)^2, rounded to nearest integer
        self._k = max(1, round((mean / std_dev) ** 2))

        for _ in range(stream_select * 1000):
            self._uniform()

    def __call__(self) -> float:
        z = 1.0
        for _ in range(self._k):
            z *= self._uniform()
        return -(self._mean / self._k) * math.log(z)


class HyperExponentialStream(RandomStream):
    """
    Hyperexponential distribution with given mean and standard deviation.

    Requires coefficient of variation (std_dev/mean) > 1.

    From Random.n:136-142.
    """

    def __init__(
        self,
        mean: float,
        std_dev: float,
        stream_select: int = 0,
        mg_seed: int = DEFAULT_MG_SEED,
        lcg_seed: int = DEFAULT_LCG_SEED,
    ) -> None:
        super().__init__(mg_seed, lcg_seed)
        self._mean = mean
        self._std_dev = std_dev

        # Calculate p from coefficient of variation
        cv = std_dev / mean
        if cv <= 1.0:
            raise ValueError(
                f"HyperExponentialStream requires CV > 1 (got {cv:.4f}). "
                "Use ExponentialStream for CV=1 or ErlangStream for CV<1."
            )
        self._p = 0.5 * (1.0 - math.sqrt((cv * cv - 1.0) / (cv * cv + 1.0)))

        for _ in range(stream_select * 1000):
            self._uniform()

    def __call__(self) -> float:
        z = self._mean / (1.0 - self._p) if self._uniform() > self._p else self._mean / self._p
        return -0.5 * z * math.log(self._uniform())


class NormalStream(RandomStream):
    """
    Normal (Gaussian) distribution with given mean and standard deviation.

    Uses Box-Muller-Marsaglia polar method (Knuth Vol 2, p.117).

    From Random.n:144-170.
    """

    def __init__(
        self,
        mean: float,
        std_dev: float,
        stream_select: int = 0,
        mg_seed: int = DEFAULT_MG_SEED,
        lcg_seed: int = DEFAULT_LCG_SEED,
    ) -> None:
        super().__init__(mg_seed, lcg_seed)
        self._mean = mean
        self._std_dev = std_dev
        self._z = 0.0  # Cached second value from pair

        for _ in range(stream_select * 1000):
            self._uniform()

    def __call__(self) -> float:
        if self._z != 0.0:
            x2 = self._z
            self._z = 0.0
        else:
            # Polar method
            while True:
                v1 = 2.0 * self._uniform() - 1.0
                v2 = 2.0 * self._uniform() - 1.0
                s = v1 * v1 + v2 * v2
                if s < 1.0:
                    break

            s = math.sqrt((-2.0 * math.log(s)) / s)
            x2 = v1 * s
            self._z = v2 * s

        return self._mean + x2 * self._std_dev


class TriangularStream(RandomStream):
    """
    Triangular distribution with lower limit a, upper limit b, and mode c.

    Requires: a < b and a <= c <= b.

    From Random.n:172-188.
    """

    def __init__(
        self,
        a: float,
        b: float,
        c: float,
        stream_select: int = 0,
        mg_seed: int = DEFAULT_MG_SEED,
        lcg_seed: int = DEFAULT_LCG_SEED,
    ) -> None:
        super().__init__(mg_seed, lcg_seed)
        self._a = a
        self._b = b
        self._c = c

        for _ in range(stream_select * 1000):
            self._uniform()

    def __call__(self) -> float:
        f = (self._c - self._a) / (self._b - self._a)
        rand = self._uniform()

        if rand < f:
            return self._a + math.sqrt(rand * (self._b - self._a) * (self._c - self._a))
        else:
            return self._b - math.sqrt((1 - rand) * (self._b - self._a) * (self._b - self._c))
