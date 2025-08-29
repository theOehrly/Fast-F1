.. _`rate_limits-caching`:

Rate Limits and Caching
=======================

All HTTP requests that are performed by FastF1 go through its caching and
rate limiting system.

Caching is enabled by default in FastF1 and most of the time, you do not need
to worry about caching at all. It will simply happen automatically in the
background and speed up your programs. Disabling the cache is highly
discouraged and will generally slow down your programs.

Rate limits are applied at all times. Requests that can be served from the
cache do not count towards any rate limits. Having the cache enabled can
therefore virtually increase the rate limits.

When rate limits are exceeded, FastF1 will either...

- throttle the rate of requests, if small delays are sufficient to stay within
  the limit (soft rate limit)

- raise a :class:`fastf1.RateLimitExceededError` (hard rate limit)


Rate Limits
-----------

ToDo explain rate limits


Cache Configuration
-------------------

.. currentmodule:: fastf1


.. autoclass:: Cache
    :members:
    :undoc-members:
    :autosummary:
