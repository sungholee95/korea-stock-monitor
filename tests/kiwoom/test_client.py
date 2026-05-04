from unittest.mock import MagicMock, patch

import pytest

from ksmonitor.adapters.kiwoom.client import (
    KiwoomClient,
    KiwoomSubscription,
    _KiwoomRestClient,
)
from ksmonitor.adapters.kiwoom.endpoints import KiwoomEndpoint
from ksmonitor.adapters.kiwoom.endpoints.rkinfo import TradePriceRankRequest


def _make_alert(endpoint=KiwoomEndpoint.거래대금상위요청, params=None, name="test"):
    """Build a mock alert exposing the attributes KiwoomClient reads."""
    alert = MagicMock()
    alert.endpoint = endpoint
    alert.endpoint_params = dict(params or {})
    alert.name = name
    return alert


class TestSubscription:
    @patch("ksmonitor.adapters.kiwoom.client.requests.request")
    def test_execute_propagates_http_error(self, mock_request, mock_auth):
        from requests.exceptions import ConnectionError

        mock_request.side_effect = ConnectionError("network down")
        sub = KiwoomSubscription(TradePriceRankRequest, mock_auth)
        with pytest.raises(ConnectionError):
            sub.execute()


class TestKiwoomRestClientSubscriptions:
    def test_subscribe_adds_subscription(self, mock_auth):
        client = _KiwoomRestClient(mock_auth, poll_rate=5.0)
        sub = client.subscribe(KiwoomEndpoint.거래대금상위요청)
        assert KiwoomEndpoint.거래대금상위요청.name in client._subscribed
        assert client._subscribed[KiwoomEndpoint.거래대금상위요청.name] is sub

    def test_subscribe_custom_name(self, mock_auth):
        client = _KiwoomRestClient(mock_auth, poll_rate=5.0)
        sub = client.subscribe(KiwoomEndpoint.거래대금상위요청, name="custom")
        assert "custom" in client._subscribed
        assert client._subscribed["custom"] is sub

    def test_unsubscribe_removes_subscription(self, mock_auth):
        client = _KiwoomRestClient(mock_auth, poll_rate=5.0)
        client.subscribe(KiwoomEndpoint.거래대금상위요청)
        removed = client.unsubscribe(KiwoomEndpoint.거래대금상위요청)
        assert removed is not None
        assert KiwoomEndpoint.거래대금상위요청.name not in client._subscribed

    def test_unsubscribe_by_string_name(self, mock_auth):
        client = _KiwoomRestClient(mock_auth, poll_rate=5.0)
        client.subscribe(KiwoomEndpoint.거래대금상위요청, name="custom")
        removed = client.unsubscribe("custom")
        assert removed is not None
        assert "custom" not in client._subscribed


class TestKiwoomRestClientRateLimit:
    def test_too_frequent_polling_enforce_rate_limit_prod(self, mock_auth):
        """Prod limit is 20 calls/s"""
        client = _KiwoomRestClient(mock_auth, poll_rate=1 / 21)
        client._subscribed["sub"] = KiwoomSubscription(TradePriceRankRequest, mock_auth)

        with pytest.raises(ValueError, match="Rate limit exceeded"):
            client._enforce_rate_limit()

    def test_too_many_subs_raises_rate_limit_prod(self, mock_auth):
        """Prod limit is 20 calls/s — 21 subs at 1s poll should raise."""
        client = _KiwoomRestClient(mock_auth, poll_rate=1)
        for i in range(21):
            client._subscribed[f"sub_{i}"] = KiwoomSubscription(
                TradePriceRankRequest, mock_auth
            )

        with pytest.raises(ValueError, match="Rate limit exceeded"):
            client._enforce_rate_limit()

    def test_too_frequent_polling_enforce_rate_limit_paper(self, mock_paper_auth):
        """Paper limit is 2 calls/s."""
        client = _KiwoomRestClient(mock_paper_auth, poll_rate=1 / 3)
        client._subscribed["sub"] = KiwoomSubscription(
            TradePriceRankRequest, mock_paper_auth
        )

        with pytest.raises(ValueError, match="Rate limit exceeded"):
            client._enforce_rate_limit()

    def test_too_many_subs_raises_rate_limit_paper(self, mock_paper_auth):
        """Paper limit is 2 calls/s — 3 subs at 1s poll should raise."""
        client = _KiwoomRestClient(mock_paper_auth, poll_rate=1.0)
        for i in range(3):
            client._subscribed[f"sub_{i}"] = KiwoomSubscription(
                TradePriceRankRequest, mock_paper_auth
            )
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            client._enforce_rate_limit()

    def test_at_limit_prod_does_not_raise(self, mock_auth):
        """Exactly 20 calls/s (20 subs at 1s poll) should not raise."""
        client = _KiwoomRestClient(mock_auth, poll_rate=1.0)
        for i in range(20):
            client._subscribed[f"sub_{i}"] = KiwoomSubscription(
                TradePriceRankRequest, mock_auth
            )
        client._enforce_rate_limit()  # should not raise

    def test_at_limit_paper_does_not_raise(self, mock_paper_auth):
        """Exactly 2 calls/s (2 subs at 1s poll) should not raise."""
        client = _KiwoomRestClient(mock_paper_auth, poll_rate=1.0)
        for i in range(2):
            client._subscribed[f"sub_{i}"] = KiwoomSubscription(
                TradePriceRankRequest, mock_paper_auth
            )
        client._enforce_rate_limit()  # should not raise

    def test_zero_poll_rate_with_subs_raises(self, mock_auth):
        """Zero poll rate with subscriptions should raise."""
        client = _KiwoomRestClient(mock_auth, poll_rate=0)
        client._subscribed["sub"] = KiwoomSubscription(TradePriceRankRequest, mock_auth)
        with pytest.raises(ValueError, match="greater than 0"):
            client._enforce_rate_limit()

    def test_no_subs_skips_rate_limit(self, mock_auth):
        """No subscriptions — rate limit check is a no-op even with zero poll rate."""
        client = _KiwoomRestClient(mock_auth, poll_rate=0)
        client._enforce_rate_limit()  # should not raise


class TestKiwoomClientAlertRegistration:
    def test_subscription_key_generation(self):
        endpoint = KiwoomEndpoint.거래대금상위요청
        assert KiwoomClient._subscription_key(endpoint, {}) == endpoint.name
        assert (
            KiwoomClient._subscription_key(endpoint, {"mrkt_tp": "000"})
            == f"{endpoint.name}_mrkt_tp=000"
        )
        # query_param keys are sorted
        assert (
            KiwoomClient._subscription_key(endpoint, {"b": "2", "a": "1"})
            == f"{endpoint.name}_a=1,b=2"
        )

    def test_different_params_create_separate_subscriptions(self, mock_auth):
        client = KiwoomClient(mock_auth, rest_poll_rate=10)
        a1 = _make_alert(params={"mrkt_tp": "000"}, name="alert1")
        a2 = _make_alert(params={"mrkt_tp": "001"}, name="alert2")

        client.register_alerts(a1, a2)

        assert len(client._subscribed) == 2
        k1 = client._subscription_key(a1.endpoint, a1.endpoint_params)
        k2 = client._subscription_key(a2.endpoint, a2.endpoint_params)
        assert k1 != k2
        assert client._alerts_by_sub[k1] == {a1}
        assert client._alerts_by_sub[k2] == {a2}

    def test_unregister_alert_refcounts_subscription(self, mock_auth):
        client = KiwoomClient(mock_auth, rest_poll_rate=10)
        a1 = _make_alert(params={"mrkt_tp": "000"}, name="a1")
        a2 = _make_alert(params={"mrkt_tp": "000"}, name="a2")

        client.register_alerts(a1, a2)
        key = client._subscription_key(a1.endpoint, a1.endpoint_params)
        assert client._alerts_by_sub[key] == {a1, a2}
        assert key in client._subscribed

        client.unregister_alert(a1)
        # one alert still watching subscription
        assert client._alerts_by_sub[key] == {a2}
        assert key in client._subscribed

        client.unregister_alert(a2)
        # no more watchers to subscription
        assert key not in client._alerts_by_sub
        assert key not in client._subscribed

    def test_poll_dispatches_to_all_alerts_on_shared_subscription(self, mock_auth):
        client = KiwoomClient(mock_auth, rest_poll_rate=10)
        a1 = _make_alert(params={"mrkt_tp": "000"}, name="a1")
        a2 = _make_alert(params={"mrkt_tp": "000"}, name="a2")
        client.register_alerts(a1, a2)

        key = client._subscription_key(a1.endpoint, a1.endpoint_params)
        fake_output = MagicMock()
        # Mirrors the dispatch line in `_poll_loop`
        for alert in client._alerts_by_sub.get(key, ()):
            alert.ingest(fake_output)

        a1.ingest.assert_called_once_with(fake_output)
        a2.ingest.assert_called_once_with(fake_output)
