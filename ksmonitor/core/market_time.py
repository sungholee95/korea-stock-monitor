from __future__ import annotations

from datetime import datetime, time, timedelta

# KRX + NXT
KST_MARKET_OPEN = time(8, 0)  # 8 AM
KST_MARKET_CLOSE = time(20, 0)  # 8 PM

# TODO: add options to specify KRX or NXT market
KRX_MARKET_OPEN = time(9, 0)
KRX_MARKET_CLOSE = time(15, 30)

NXT_MARKET_OPEN = time(8, 0)
NXT_MARKET_CLOSE = time(20, 0)


def bucket_start(dt: datetime, minutes: int) -> datetime:
    """Return the start time of bucket for `dt`, where bucket
    is of size `minutes` and anchored at `KST_MARKET_OPEN`
    """
    if minutes <= 0:
        raise ValueError(f"`minutes` must be positive, got {minutes!r}")

    anchor = datetime.combine(dt.date(), KST_MARKET_OPEN)
    elapsed = dt - anchor
    bucket_idx = elapsed // timedelta(minutes=minutes)

    return anchor + bucket_idx * timedelta(minutes=minutes)


def bucket_index(dt: datetime, minutes: int) -> int:
    """Return the index of the bucket containing `dt`.
    Useful for detecting bucket transitions.
    """
    anchor = datetime.combine(dt.date(), KST_MARKET_OPEN)
    elapsed = dt - anchor
    return int(elapsed // timedelta(minutes=minutes))
