from dataclasses import dataclass, field
from typing import ClassVar

from ._base import (
    KISBaseRestRequest,
    KISBaseRestResponse,
    KISBaseRestResponseOutput,
)
from ._common import KISEndpoint


@dataclass(repr=False)
class InquirePriceResponseOutput(KISBaseRestResponseOutput):
    """주식현재가 시세[v1_국내주식-008] response body output"""

    output_raw: dict[str, str]  # single object, not list

    iscd_stat_cls_code: str = field(init=False, metadata={"ko": "종목 상태 구분 코드"})
    marg_rate: float = field(init=False, metadata={"ko": "증거금 비율"})
    rprs_mrkt_kor_name: str = field(init=False, metadata={"ko": "대표 시장 한글 명"})
    bstp_kor_isnm: str = field(init=False, metadata={"ko": "업종 한글 종목명"})
    temp_stop_yn: bool = field(init=False, metadata={"ko": "임시 정지 여부"})
    oprc_rang_cont_yn: bool = field(init=False, metadata={"ko": "시가 범위 연장 여부"})
    clpr_rang_cont_yn: bool = field(init=False, metadata={"ko": "종가 범위 연장 여부"})
    crdt_able_yn: bool = field(init=False, metadata={"ko": "신용 가능 여부"})
    grmn_rate_cls_code: str = field(
        init=False, metadata={"ko": "보증금 비율 구분 코드"}
    )
    elw_pblc_yn: bool = field(init=False, metadata={"ko": "ELW 발행 여부"})
    stck_prpr: int = field(init=False, metadata={"ko": "주식 현재가"})
    prdy_vrss: int = field(init=False, metadata={"ko": "전일 대비"})
    prdy_vrss_sign: str = field(init=False, metadata={"ko": "전일 대비 부호"})
    prdy_ctrt: float = field(init=False, metadata={"ko": "전일 대비율"})
    acml_tr_pbmn: int = field(init=False, metadata={"ko": "누적 거래 대금"})
    acml_vol: int = field(init=False, metadata={"ko": "누적 거래량"})
    prdy_vrss_vol_rate: float = field(
        init=False, metadata={"ko": "전일 대비 거래량 비율"}
    )
    stck_oprc: int = field(init=False, metadata={"ko": "주식 시가"})
    stck_hgpr: int = field(init=False, metadata={"ko": "주식 최고가"})
    stck_lwpr: int = field(init=False, metadata={"ko": "주식 최저가"})
    stck_mxpr: int = field(init=False, metadata={"ko": "주식 상한가"})
    stck_llam: int = field(init=False, metadata={"ko": "주식 하한가"})
    stck_sdpr: int = field(init=False, metadata={"ko": "주식 기준가"})
    wghn_avrg_stck_prc: int = field(init=False, metadata={"ko": "가중 평균 주식 가격"})
    hts_frgn_ehrt: float = field(init=False, metadata={"ko": "HTS 외국인 소진율"})
    frgn_ntby_qty: int = field(init=False, metadata={"ko": "외국인 순매수 수량"})
    pgtr_ntby_qty: int = field(init=False, metadata={"ko": "프로그램매매 순매수 수량"})
    pvt_scnd_dmrs_prc: int = field(init=False, metadata={"ko": "피벗 2차 디저항 가격"})
    pvt_frst_dmrs_prc: int = field(init=False, metadata={"ko": "피벗 1차 디저항 가격"})
    pvt_pont_val: float = field(init=False, metadata={"ko": "피벗 포인트 값"})
    pvt_frst_dmsp_prc: int = field(init=False, metadata={"ko": "피벗 1차 디지지 가격"})
    pvt_scnd_dmsp_prc: int = field(init=False, metadata={"ko": "피벗 2차 디지지 가격"})
    dmrs_val: float = field(init=False, metadata={"ko": "디저항 값"})
    dmsp_val: float = field(init=False, metadata={"ko": "디지지 값"})
    cpfn: int = field(init=False, metadata={"ko": "자본금"})
    rstc_wdth_prc: int = field(init=False, metadata={"ko": "제한 폭 가격"})
    stck_fcam: int = field(init=False, metadata={"ko": "주식 액면가"})
    stck_sspr: int = field(init=False, metadata={"ko": "주식 대용가"})
    aspr_unit: str = field(init=False, metadata={"ko": "호가단위"})
    hts_deal_qty_unit_val: int = field(
        init=False, metadata={"ko": "HTS 매매 수량 단위 값"}
    )
    lstn_stcn: int = field(init=False, metadata={"ko": "상장 주수"})
    hts_avls: int = field(init=False, metadata={"ko": "HTS 시가총액"})
    per: float = field(init=False, metadata={"ko": "PER"})
    pbr: float = field(init=False, metadata={"ko": "PBR"})
    stac_month: str = field(init=False, metadata={"ko": "결산 월"})
    vol_tnrt: float = field(init=False, metadata={"ko": "거래량 회전율"})
    eps: float = field(init=False, metadata={"ko": "EPS"})
    bps: float = field(init=False, metadata={"ko": "BPS"})
    d250_hgpr: int = field(init=False, metadata={"ko": "250일 최고가"})
    d250_hgpr_date: str = field(init=False, metadata={"ko": "250일 최고가 일자"})
    d250_hgpr_vrss_prpr_rate: float = field(
        init=False, metadata={"ko": "250일 최고가 대비 현재가 비율"}
    )
    d250_lwpr: int = field(init=False, metadata={"ko": "250일 최저가"})
    d250_lwpr_date: str = field(init=False, metadata={"ko": "250일 최저가 일자"})
    d250_lwpr_vrss_prpr_rate: float = field(
        init=False, metadata={"ko": "250일 최저가 대비 현재가 비율"}
    )
    stck_dryy_hgpr: int = field(init=False, metadata={"ko": "주식 연중 최고가"})
    dryy_hgpr_vrss_prpr_rate: float = field(
        init=False, metadata={"ko": "연중 최고가 대비 현재가 비율"}
    )
    dryy_hgpr_date: str = field(init=False, metadata={"ko": "연중 최고가 일자"})
    stck_dryy_lwpr: int = field(init=False, metadata={"ko": "주식 연중 최저가"})
    dryy_lwpr_vrss_prpr_rate: float = field(
        init=False, metadata={"ko": "연중 최저가 대비 현재가 비율"}
    )
    dryy_lwpr_date: str = field(init=False, metadata={"ko": "연중 최저가 일자"})
    w52_hgpr: int = field(init=False, metadata={"ko": "52주일 최고가"})
    w52_hgpr_vrss_prpr_ctrt: float = field(
        init=False, metadata={"ko": "52주일 최고가 대비 현재가 대비"}
    )
    w52_hgpr_date: str = field(init=False, metadata={"ko": "52주일 최고가 일자"})
    w52_lwpr: int = field(init=False, metadata={"ko": "52주일 최저가"})
    w52_lwpr_vrss_prpr_ctrt: float = field(
        init=False, metadata={"ko": "52주일 최저가 대비 현재가 대비"}
    )
    w52_lwpr_date: str = field(init=False, metadata={"ko": "52주일 최저가 일자"})
    whol_loan_rmnd_rate: float = field(
        init=False, metadata={"ko": "전체 융자 잔고 비율"}
    )
    ssts_yn: bool = field(init=False, metadata={"ko": "공매도가능여부"})
    stck_shrn_iscd: str = field(init=False, metadata={"ko": "주식 단축 종목코드"})
    fcam_cnnm: str = field(init=False, metadata={"ko": "액면가 통화명"})
    cpfn_cnnm: str = field(init=False, metadata={"ko": "자본금 통화명"})
    frgn_hldn_qty: int = field(init=False, metadata={"ko": "외국인 보유 수량"})
    vi_cls_code: str = field(init=False, metadata={"ko": "VI적용구분코드"})
    ovtm_vi_cls_code: str = field(
        init=False, metadata={"ko": "시간외단일가VI적용구분코드"}
    )
    last_ssts_cntg_qty: int = field(
        init=False, metadata={"ko": "최종 공매도 체결 수량"}
    )
    invt_caful_yn: bool = field(init=False, metadata={"ko": "투자유의여부"})
    mrkt_warn_cls_code: str = field(init=False, metadata={"ko": "시장경고코드"})
    short_over_yn: bool = field(init=False, metadata={"ko": "단기과열여부"})
    sltr_yn: bool = field(init=False, metadata={"ko": "정리매매여부"})
    mang_issu_cls_code: str = field(init=False, metadata={"ko": "관리종목여부"})

    def __post_init__(self):
        unexpected, missing = self._check_keys()

        self.iscd_stat_cls_code = str(self.output_raw["iscd_stat_cls_code"])
        self.marg_rate = float(self.output_raw["marg_rate"])
        self.rprs_mrkt_kor_name = str(self.output_raw["rprs_mrkt_kor_name"])
        self.bstp_kor_isnm = str(self.output_raw["bstp_kor_isnm"])
        self.temp_stop_yn = self.output_raw["temp_stop_yn"] == "Y"
        self.oprc_rang_cont_yn = self.output_raw["oprc_rang_cont_yn"] == "Y"
        self.clpr_rang_cont_yn = self.output_raw["clpr_rang_cont_yn"] == "Y"
        self.crdt_able_yn = self.output_raw["crdt_able_yn"] == "Y"
        self.grmn_rate_cls_code = str(self.output_raw["grmn_rate_cls_code"])
        self.elw_pblc_yn = self.output_raw["elw_pblc_yn"] == "Y"
        self.stck_prpr = int(self.output_raw["stck_prpr"])
        self.prdy_vrss = int(self.output_raw["prdy_vrss"])
        self.prdy_vrss_sign = str(self.output_raw["prdy_vrss_sign"])
        self.prdy_ctrt = float(self.output_raw["prdy_ctrt"])
        self.acml_tr_pbmn = int(self.output_raw["acml_tr_pbmn"])
        self.acml_vol = int(self.output_raw["acml_vol"])
        self.prdy_vrss_vol_rate = float(self.output_raw["prdy_vrss_vol_rate"])
        self.stck_oprc = int(self.output_raw["stck_oprc"])
        self.stck_hgpr = int(self.output_raw["stck_hgpr"])
        self.stck_lwpr = int(self.output_raw["stck_lwpr"])
        self.stck_mxpr = int(self.output_raw["stck_mxpr"])
        self.stck_llam = int(self.output_raw["stck_llam"])
        self.stck_sdpr = int(self.output_raw["stck_sdpr"])
        self.wghn_avrg_stck_prc = int(self.output_raw["wghn_avrg_stck_prc"])
        self.hts_frgn_ehrt = float(self.output_raw["hts_frgn_ehrt"])
        self.frgn_ntby_qty = int(self.output_raw["frgn_ntby_qty"])
        self.pgtr_ntby_qty = int(self.output_raw["pgtr_ntby_qty"])
        self.pvt_scnd_dmrs_prc = int(self.output_raw["pvt_scnd_dmrs_prc"])
        self.pvt_frst_dmrs_prc = int(self.output_raw["pvt_frst_dmrs_prc"])
        self.pvt_pont_val = float(self.output_raw["pvt_pont_val"])
        self.pvt_frst_dmsp_prc = int(self.output_raw["pvt_frst_dmsp_prc"])
        self.pvt_scnd_dmsp_prc = int(self.output_raw["pvt_scnd_dmsp_prc"])
        self.dmrs_val = float(self.output_raw["dmrs_val"])
        self.dmsp_val = float(self.output_raw["dmsp_val"])
        self.cpfn = int(self.output_raw["cpfn"])
        self.rstc_wdth_prc = int(self.output_raw["rstc_wdth_prc"])
        self.stck_fcam = int(self.output_raw["stck_fcam"])
        self.stck_sspr = int(self.output_raw["stck_sspr"])
        self.aspr_unit = str(self.output_raw["aspr_unit"])
        self.hts_deal_qty_unit_val = int(self.output_raw["hts_deal_qty_unit_val"])
        self.lstn_stcn = int(self.output_raw["lstn_stcn"])
        self.hts_avls = int(self.output_raw["hts_avls"])
        self.per = float(self.output_raw["per"])
        self.pbr = float(self.output_raw["pbr"])
        self.stac_month = str(self.output_raw["stac_month"])
        self.vol_tnrt = float(self.output_raw["vol_tnrt"])
        self.eps = float(self.output_raw["eps"])
        self.bps = float(self.output_raw["bps"])
        self.d250_hgpr = int(self.output_raw["d250_hgpr"])
        self.d250_hgpr_date = str(self.output_raw["d250_hgpr_date"])
        self.d250_hgpr_vrss_prpr_rate = float(
            self.output_raw["d250_hgpr_vrss_prpr_rate"]
        )
        self.d250_lwpr = int(self.output_raw["d250_lwpr"])
        self.d250_lwpr_date = str(self.output_raw["d250_lwpr_date"])
        self.d250_lwpr_vrss_prpr_rate = float(
            self.output_raw["d250_lwpr_vrss_prpr_rate"]
        )
        self.stck_dryy_hgpr = int(self.output_raw["stck_dryy_hgpr"])
        self.dryy_hgpr_vrss_prpr_rate = float(
            self.output_raw["dryy_hgpr_vrss_prpr_rate"]
        )
        self.dryy_hgpr_date = str(self.output_raw["dryy_hgpr_date"])
        self.stck_dryy_lwpr = int(self.output_raw["stck_dryy_lwpr"])
        self.dryy_lwpr_vrss_prpr_rate = float(
            self.output_raw["dryy_lwpr_vrss_prpr_rate"]
        )
        self.dryy_lwpr_date = str(self.output_raw["dryy_lwpr_date"])
        self.w52_hgpr = int(self.output_raw["w52_hgpr"])
        self.w52_hgpr_vrss_prpr_ctrt = float(self.output_raw["w52_hgpr_vrss_prpr_ctrt"])
        self.w52_hgpr_date = str(self.output_raw["w52_hgpr_date"])
        self.w52_lwpr = int(self.output_raw["w52_lwpr"])
        self.w52_lwpr_vrss_prpr_ctrt = float(self.output_raw["w52_lwpr_vrss_prpr_ctrt"])
        self.w52_lwpr_date = str(self.output_raw["w52_lwpr_date"])
        self.whol_loan_rmnd_rate = float(self.output_raw["whol_loan_rmnd_rate"])
        self.ssts_yn = self.output_raw["ssts_yn"] == "Y"
        self.stck_shrn_iscd = str(self.output_raw["stck_shrn_iscd"])
        self.fcam_cnnm = str(self.output_raw["fcam_cnnm"])
        self.cpfn_cnnm = str(self.output_raw["cpfn_cnnm"])
        self.frgn_hldn_qty = int(self.output_raw["frgn_hldn_qty"])
        self.vi_cls_code = str(self.output_raw["vi_cls_code"])
        self.ovtm_vi_cls_code = str(self.output_raw["ovtm_vi_cls_code"])
        self.last_ssts_cntg_qty = int(self.output_raw["last_ssts_cntg_qty"])
        self.invt_caful_yn = self.output_raw["invt_caful_yn"] == "Y"
        self.mrkt_warn_cls_code = str(self.output_raw["mrkt_warn_cls_code"])
        self.short_over_yn = self.output_raw["short_over_yn"] == "Y"
        self.sltr_yn = self.output_raw["sltr_yn"] == "Y"
        self.mang_issu_cls_code = str(self.output_raw["mang_issu_cls_code"])


@dataclass(init=False)
class InquirePriceResponse(KISBaseRestResponse):
    _endpoint: ClassVar[KISEndpoint] = KISEndpoint.INQUIRE_PRICE_REST
    _output_schema: ClassVar[type[InquirePriceResponseOutput]] = (
        InquirePriceResponseOutput
    )
    output: InquirePriceResponseOutput


@dataclass(kw_only=True)
class InquirePriceRequest(KISBaseRestRequest):
    """주식현재가 시세[v1_국내주식-008]
    https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/quotations/inquire-price
    """

    _endpoint: ClassVar[KISEndpoint] = KISEndpoint.INQUIRE_PRICE_REST
    _response_spec: ClassVar[type[InquirePriceResponse]] = InquirePriceResponse

    # required query params
    fid_input_iscd: str  # 입력 종목코드; 종목코드 (ex 005930 삼성전자) // ETN은 종목코드 6자리 앞에 Q 입력 필수

    # default query params (can be overridden)
    fid_cond_mrkt_div_code: str = "J"  # 조건 시장 분류 코드; J:KRX, NX:NXT, UN:통합

    def get_headers(self) -> dict[str, str]:
        """Headers filled by Auth class. Call Auth.get_rest_headers() to populate."""
        return super()._get_base_headers()

    def get_query_params(self) -> dict[str, str]:
        return {
            "FID_COND_MRKT_DIV_CODE": self.fid_cond_mrkt_div_code,
            "FID_INPUT_ISCD": self.fid_input_iscd,
        }
