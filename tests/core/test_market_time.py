from datetime import datetime

import pytest

from ksmonitor.core import market_time


class TestBucketStart:
    @pytest.mark.parametrize(
        ("when", "minutes", "expected"),
        [
            (datetime(2026, 1, 1, 8, 0, 30), 1, datetime(2026, 1, 1, 8, 0, 0)),
            (datetime(2026, 1, 1, 9, 1, 30), 1, datetime(2026, 1, 1, 9, 1, 0)),
            (datetime(2026, 1, 1, 10, 23, 45), 5, datetime(2026, 1, 1, 10, 20, 0)),
            (datetime(2026, 1, 1, 8, 7, 15), 5, datetime(2026, 1, 1, 8, 5, 0)),
            # Exactly at a bucket boundary
            (datetime(2026, 1, 1, 8, 0, 0), 1, datetime(2026, 1, 1, 8, 0, 0)),
            (datetime(2026, 1, 1, 8, 5, 0), 5, datetime(2026, 1, 1, 8, 5, 0)),
        ],
    )
    def test_aligned_to_market_open(self, when, minutes, expected):
        assert market_time.bucket_start(when, minutes=minutes) == expected

    def test_before_market_open_rolls_back(self):
        # 07:59:30 is one second before anchor 08:00:00 with a 1-min bucket
        when = datetime(2026, 1, 1, 7, 59, 30)
        assert market_time.bucket_start(when, minutes=1) == datetime(
            2026, 1, 1, 7, 59, 0
        )

    def test_non_positive_minutes_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            market_time.bucket_start(datetime(2026, 1, 1, 9, 0), minutes=0)


class TestBucketIndex:
    def test_bucket_index_increments_per_window(self):
        # Same day, bucket 0 at 08:00
        t0 = datetime(2026, 1, 1, 8, 0, 0)
        assert market_time.bucket_index(t0, minutes=1) == 0

        # 1 minute later, bucket 1
        t1 = datetime(2026, 1, 1, 8, 1, 0)
        assert market_time.bucket_index(t1, minutes=1) == 1

        # Within bucket 1
        t1_mid = datetime(2026, 1, 1, 8, 1, 30)
        assert market_time.bucket_index(t1_mid, minutes=1) == 1

        # 5-minute window
        t0 = datetime(2026, 1, 1, 8, 0, 0)
        assert market_time.bucket_index(t0, minutes=5) == 0

        t5 = datetime(2026, 1, 1, 8, 5, 0)
        assert market_time.bucket_index(t5, minutes=5) == 1

        t5_1 = datetime(2026, 1, 1, 8, 5, 1)
        assert market_time.bucket_index(t5_1, minutes=5) == 1

        t4_59 = datetime(2026, 1, 1, 8, 4, 59)
        assert market_time.bucket_index(t4_59, minutes=5) == 0
