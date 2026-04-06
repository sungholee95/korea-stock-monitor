from typing import TYPE_CHECKING

from ksmonitor.adapters.kiwoom.endpoints import KiwoomEndpoint
from ksmonitor.adapters.kiwoom.endpoints._common import REQUEST_REGISTRY
from ksmonitor.adapters.kiwoom.endpoints.rkinfo import (
    TradePriceRankRequest,
    TradePriceRankResponse,
)

if TYPE_CHECKING:
    from ksmonitor.adapters.kiwoom.auth import KiwoomAuth


class TestRequestRegistry:
    def test_rest_endpoints_are_registered(self):
        assert KiwoomEndpoint.거래대금상위요청 in REQUEST_REGISTRY

    def test_get_request_spec_returns_correct_class(self):
        assert (
            KiwoomEndpoint.거래대금상위요청.get_request_spec() is TradePriceRankRequest
        )

    def test_request_registers_output(self):
        assert (
            KiwoomEndpoint.거래대금상위요청.get_request_spec()._response_spec
            is TradePriceRankResponse
        )


class TestRequestBuilding:
    def test_request_headers(self, mock_auth: KiwoomAuth):
        spec = KiwoomEndpoint.거래대금상위요청.get_request_spec()
        req = spec(auth=mock_auth)
        assert req.get_headers() == {
            "authorization": "Bearer fake_token",
            "Content-Type": "application/json;charset=UTF-8",
            "api-id": "ka10032",
        }

    def test_request_default_query_params(self, mock_auth: KiwoomAuth):
        spec = KiwoomEndpoint.거래대금상위요청.get_request_spec()
        req = spec(auth=mock_auth)
        assert req.get_query_params() == {
            "mrkt_tp": "000",
            "mang_stk_incls": "1",
            "stex_tp": "3",
        }

    def test_request_override_default_query_params(self, mock_auth: KiwoomAuth):
        spec = KiwoomEndpoint.거래대금상위요청.get_request_spec()
        query_params = {"mrkt_tp": "010", "mang_stk_incls": "8", "stex_tp": "9"}
        req = spec(auth=mock_auth, **query_params)
        assert req.get_query_params() == query_params
