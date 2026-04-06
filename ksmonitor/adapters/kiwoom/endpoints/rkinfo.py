from dataclasses import dataclass, field
from typing import ClassVar

from ._base import (
    KiwoomBaseRestRequest,
    KiwoomBaseRestResponse,
    KiwoomBaseRestResponseOutput,
)
from ._common import KiwoomEndpoint


@dataclass(repr=False)
class TradePriceRankResponseOutput(KiwoomBaseRestResponseOutput):
    """국내주식 > 순위정보 > 거래대금상위요청(ka10032) response body output"""

    output_raw: list[dict[str, str]]

    stk_cd: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "종목코드"}
    )
    now_rank: list[int] = field(
        default_factory=list, init=False, metadata={"ko": "현재순위"}
    )
    pred_rank: list[int] = field(
        default_factory=list, init=False, metadata={"ko": "전일순위"}
    )
    stk_nm: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "종목명"}
    )
    cur_prc: list[float] = field(
        default_factory=list, init=False, metadata={"ko": "현재가"}
    )
    pred_pre_sig: list[float] = field(
        default_factory=list, init=False, metadata={"ko": "전일대비기호"}
    )
    pred_pre: list[float] = field(
        default_factory=list, init=False, metadata={"ko": "전일대비"}
    )
    flu_rt: list[float] = field(
        default_factory=list, init=False, metadata={"ko": "등락률"}
    )
    sel_bid: list[float] = field(
        default_factory=list, init=False, metadata={"ko": "매도호가"}
    )
    buy_bid: list[float] = field(
        default_factory=list, init=False, metadata={"ko": "매수호가"}
    )
    now_trde_qty: list[float] = field(
        default_factory=list, init=False, metadata={"ko": "현재거래량"}
    )
    pred_trde_qty: list[float] = field(
        default_factory=list, init=False, metadata={"ko": "전일거래량"}
    )
    trde_prica: list[float] = field(
        default_factory=list, init=False, metadata={"ko": "거래대금"}
    )

    def __post_init__(self):
        for item in self.output_raw:
            self.stk_cd.append(item.get("stk_cd", ""))
            self.now_rank.append(int(item.get("now_rank", 0)))
            self.pred_rank.append(int(item.get("pred_rank", 0)))
            self.stk_nm.append(item.get("stk_nm", ""))
            self.cur_prc.append(float(item.get("cur_prc", 0)))
            self.pred_pre_sig.append(float(item.get("pred_pre_sig", 0)))
            self.pred_pre.append(float(item.get("pred_pre", 0)))
            self.flu_rt.append(float(item.get("flu_rt", 0)))
            self.sel_bid.append(float(item.get("sel_bid", 0)))
            self.buy_bid.append(float(item.get("buy_bid", 0)))
            self.now_trde_qty.append(float(item.get("now_trde_qty", 0)))
            self.pred_trde_qty.append(float(item.get("pred_trde_qty", 0)))
            self.trde_prica.append(float(item.get("trde_prica", 0)))


@dataclass(init=False)
class TradePriceRankResponse(KiwoomBaseRestResponse):
    _endpoint: ClassVar[KiwoomEndpoint] = KiwoomEndpoint.거래대금상위요청
    _output_schema: ClassVar[type[TradePriceRankResponseOutput]] = (
        TradePriceRankResponseOutput
    )
    _output_key = "trde_prica_upper"
    output: TradePriceRankResponseOutput


@dataclass(kw_only=True)
class TradePriceRankRequest(KiwoomBaseRestRequest):
    """순위정보 > 거래대금상위요청 (ka10032)
    /api/dostk/rkinfo
    """

    _endpoint: ClassVar[KiwoomEndpoint] = KiwoomEndpoint.거래대금상위요청
    _response_spec: ClassVar[type[TradePriceRankResponse]] = TradePriceRankResponse

    # default query params (can be overridden)
    mrkt_tp: str = "000"  # 시장구분; 000:전체, 001:코스피, 101:코스닥
    mang_stk_incls: str = "1"  # 관리종목포함; 0:관리종목 미포함, 1:관리종목 포함
    stex_tp: str = "3"  # 거래소구분; 1:KRX, 2:NXT 3.통합

    def get_headers(self) -> dict[str, str]:
        headers = super()._get_base_headers()
        return headers

    def get_query_params(self) -> dict[str, str]:
        query = {
            "mrkt_tp": self.mrkt_tp,
            "mang_stk_incls": self.mang_stk_incls,
            "stex_tp": self.stex_tp,
        }

        return query
