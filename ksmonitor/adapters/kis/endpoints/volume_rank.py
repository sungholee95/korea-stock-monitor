from dataclasses import dataclass, field
from typing import ClassVar

from ._base import (
    KISBaseRestRequest,
    KISBaseRestResponse,
    KISBaseRestResponseOutput,
)
from ._common import KISEndpoint


@dataclass(repr=False)
class VolumeRankResponseOutput(KISBaseRestResponseOutput):
    """거래량순위[v1_국내주식-047] response body output"""

    output_raw: list[dict[str, str]]

    hts_kor_isnm: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "HTS 한글 종목명"}
    )
    mksc_shrn_iscd: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "유가증권 단축 종목코드"}
    )
    data_rank: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "데이터 순위"}
    )
    stck_prpr: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "주식 현재가"}
    )
    prdy_vrss_sign: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "전일 대비 부호"}
    )
    prdy_vrss: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "전일 대비"}
    )
    prdy_ctrt: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "전일 대비율"}
    )
    acml_vol: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "누적 거래량"}
    )
    prdy_vol: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "전일 거래량"}
    )
    lstn_stcn: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "상장 주수"}
    )
    avrg_vol: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "평균 거래량"}
    )
    n_befr_clpr_vrss_prpr_rate: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "N일전종가대비현재가대비율"}
    )
    vol_inrt: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "거래량증가율"}
    )
    vol_tnrt: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "거래량 회전율"}
    )
    nday_vol_tnrt: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "N일 거래량 회전율"}
    )
    avrg_tr_pbmn: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "평균 거래 대금"}
    )
    tr_pbmn_tnrt: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "거래대금회전율"}
    )
    nday_tr_pbmn_tnrt: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "N일 거래대금 회전율"}
    )
    acml_tr_pbmn: list[str] = field(
        default_factory=list, init=False, metadata={"ko": "누적 거래 대금"}
    )

    def __post_init__(self):
        unexpected, missing = self._check_keys()

        for item in self.output_raw:
            self.hts_kor_isnm.append(item["hts_kor_isnm"])
            self.mksc_shrn_iscd.append(item["mksc_shrn_iscd"])
            self.data_rank.append(item["data_rank"])
            self.stck_prpr.append(item["stck_prpr"])
            self.prdy_vrss_sign.append(item["prdy_vrss_sign"])
            self.prdy_vrss.append(item["prdy_vrss"])
            self.prdy_ctrt.append(item["prdy_ctrt"])
            self.acml_vol.append(item["acml_vol"])
            self.prdy_vol.append(item["prdy_vol"])
            self.lstn_stcn.append(item["lstn_stcn"])
            self.avrg_vol.append(item["avrg_vol"])
            self.n_befr_clpr_vrss_prpr_rate.append(item["n_befr_clpr_vrss_prpr_rate"])
            self.vol_inrt.append(item["vol_inrt"])
            self.vol_tnrt.append(item["vol_tnrt"])
            self.nday_vol_tnrt.append(item["nday_vol_tnrt"])
            self.avrg_tr_pbmn.append(item["avrg_tr_pbmn"])
            self.tr_pbmn_tnrt.append(item["tr_pbmn_tnrt"])
            self.nday_tr_pbmn_tnrt.append(item["nday_tr_pbmn_tnrt"])
            self.acml_tr_pbmn.append(item["acml_tr_pbmn"])


@dataclass(init=False)
class VolumeRankResponse(KISBaseRestResponse):
    _endpoint: ClassVar[KISEndpoint] = KISEndpoint.VOLUME_RANK_REST
    _output_schema: ClassVar[type[VolumeRankResponseOutput]] = VolumeRankResponseOutput
    output: VolumeRankResponseOutput


@dataclass(kw_only=True)
class VolumeRankRequest(KISBaseRestRequest):
    """거래량순위[v1_국내주식-047]
    https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/quotations/volume-rank
    """

    _endpoint: ClassVar[KISEndpoint] = KISEndpoint.VOLUME_RANK_REST
    _response_spec: ClassVar[type[VolumeRankResponse]] = VolumeRankResponse

    # fixed query params
    fid_cond_scr_div_code: str = field(init=False, default="20171")
    fid_input_date_1: str = field(init=False, default="")  # ""(공란) 입력

    # default query params (can be overridden)
    fid_cond_mrkt_div_code: str = "J"  # 조건 시장 분류 코드; J:KRX, NX:NXT
    fid_input_iscd: str = "0000"  # 입력 종목코드; 0000(전체) 기타(업종코드)
    fid_div_cls_code: str = "0"  # 분류 구분 코드; 0(전체) 1(보통주) 2(우선주)
    fid_blng_cls_code: str = "3"  # 소속 구분 코드; 0: 평균거래량 1:거래증가율 2:평균거래회전율 3:거래금액순 4:평균거래금액회전율
    fid_trgt_cls_code: str = "111111111"  # 대상 구분 코드; 1 or 0 9자리 (차례대로 증거금 30% 40% 50% 60% 100% 신용보증금 30% 40% 50% 60%)
    fid_trgt_exls_cls_code: str = "1100000000"  # 대상 제외 구분 코드; 1 or 0 10자리 (차례대로 투자위험/경고/주의 관리종목 정리매매 불성실공시 우선주 거래정지 ETF ETN 신용주문불가 SPAC)
    fid_input_price_1: str = "5000"  # 최저 가격 ("" 이면 전체)
    fid_input_price_2: str = ""  # 최고 가격 ("" 이면 전체)
    fid_vol_cnt: str = ""  # 거래량 수 ("" 이면 전체)

    def headers(self) -> dict[str, str]:
        headers = super()._base_headers()
        return headers

    def query_params(self) -> dict[str, str]:
        query = {
            "FID_COND_MRKT_DIV_CODE": self.fid_cond_mrkt_div_code,
            "FID_COND_SCR_DIV_CODE": self.fid_cond_scr_div_code,
            "FID_INPUT_ISCD": self.fid_input_iscd,
            "FID_DIV_CLS_CODE": self.fid_div_cls_code,
            "FID_BLNG_CLS_CODE": self.fid_blng_cls_code,
            "FID_TRGT_CLS_CODE": self.fid_trgt_cls_code,
            "FID_TRGT_EXLS_CLS_CODE": self.fid_trgt_exls_cls_code,
            "FID_INPUT_PRICE_1": self.fid_input_price_1,
            "FID_INPUT_PRICE_2": self.fid_input_price_2,
            "FID_VOL_CNT": self.fid_vol_cnt,
            "FID_INPUT_DATE_1": self.fid_input_date_1,
        }

        return query
