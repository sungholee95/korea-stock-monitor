from dataclasses import dataclass, field
from typing import ClassVar

from ._base import (
    BaseRestRequest,
    BaseRestResponse,
    BaseRestResponseOutput,
)
from ._common import KISEndpoint


@dataclass
class InquirePriceResponseOutput(BaseRestResponseOutput):
    """주식현재가 시세[v1_국내주식-008] response body output"""

    output_raw: dict[str, str]  # single object, not list

    iscd_stat_cls_code: str = field(
        default="", init=False, metadata={"ko": "종목 상태 구분 코드"}
    )
    marg_rate: str = field(default="", init=False, metadata={"ko": "증거금 비율"})
    rprs_mrkt_kor_name: str = field(
        default="", init=False, metadata={"ko": "대표 시장 한글 명"}
    )
    bstp_kor_isnm: str = field(
        default="", init=False, metadata={"ko": "업종 한글 종목명"}
    )
    temp_stop_yn: str = field(default="", init=False, metadata={"ko": "임시 정지 여부"})
    oprc_rang_cont_yn: str = field(
        default="", init=False, metadata={"ko": "시가 범위 연장 여부"}
    )
    clpr_rang_cont_yn: str = field(
        default="", init=False, metadata={"ko": "종가 범위 연장 여부"}
    )
    crdt_able_yn: str = field(default="", init=False, metadata={"ko": "신용 가능 여부"})
    grmn_rate_cls_code: str = field(
        default="", init=False, metadata={"ko": "보증금 비율 구분 코드"}
    )
    elw_pblc_yn: str = field(default="", init=False, metadata={"ko": "ELW 발행 여부"})
    stck_prpr: str = field(default="", init=False, metadata={"ko": "주식 현재가"})
    prdy_vrss: str = field(default="", init=False, metadata={"ko": "전일 대비"})
    prdy_vrss_sign: str = field(
        default="", init=False, metadata={"ko": "전일 대비 부호"}
    )
    prdy_ctrt: str = field(default="", init=False, metadata={"ko": "전일 대비율"})
    acml_tr_pbmn: str = field(default="", init=False, metadata={"ko": "누적 거래 대금"})
    acml_vol: str = field(default="", init=False, metadata={"ko": "누적 거래량"})
    prdy_vrss_vol_rate: str = field(
        default="", init=False, metadata={"ko": "전일 대비 거래량 비율"}
    )
    stck_oprc: str = field(default="", init=False, metadata={"ko": "주식 시가"})
    stck_hgpr: str = field(default="", init=False, metadata={"ko": "주식 최고가"})
    stck_lwpr: str = field(default="", init=False, metadata={"ko": "주식 최저가"})
    stck_mxpr: str = field(default="", init=False, metadata={"ko": "주식 상한가"})
    stck_llam: str = field(default="", init=False, metadata={"ko": "주식 하한가"})
    stck_sdpr: str = field(default="", init=False, metadata={"ko": "주식 기준가"})
    wghn_avrg_stck_prc: str = field(
        default="", init=False, metadata={"ko": "가중 평균 주식 가격"}
    )
    hts_frgn_ehrt: str = field(
        default="", init=False, metadata={"ko": "HTS 외국인 소진율"}
    )
    frgn_ntby_qty: str = field(
        default="", init=False, metadata={"ko": "외국인 순매수 수량"}
    )
    pgtr_ntby_qty: str = field(
        default="", init=False, metadata={"ko": "프로그램매매 순매수 수량"}
    )
    pvt_scnd_dmrs_prc: str = field(
        default="", init=False, metadata={"ko": "피벗 2차 디저항 가격"}
    )
    pvt_frst_dmrs_prc: str = field(
        default="", init=False, metadata={"ko": "피벗 1차 디저항 가격"}
    )
    pvt_pont_val: str = field(default="", init=False, metadata={"ko": "피벗 포인트 값"})
    pvt_frst_dmsp_prc: str = field(
        default="", init=False, metadata={"ko": "피벗 1차 디지지 가격"}
    )
    pvt_scnd_dmsp_prc: str = field(
        default="", init=False, metadata={"ko": "피벗 2차 디지지 가격"}
    )
    dmrs_val: str = field(default="", init=False, metadata={"ko": "디저항 값"})
    dmsp_val: str = field(default="", init=False, metadata={"ko": "디지지 값"})
    cpfn: str = field(default="", init=False, metadata={"ko": "자본금"})
    rstc_wdth_prc: str = field(default="", init=False, metadata={"ko": "제한 폭 가격"})
    stck_fcam: str = field(default="", init=False, metadata={"ko": "주식 액면가"})
    stck_sspr: str = field(default="", init=False, metadata={"ko": "주식 대용가"})
    aspr_unit: str = field(default="", init=False, metadata={"ko": "호가단위"})
    hts_deal_qty_unit_val: str = field(
        default="", init=False, metadata={"ko": "HTS 매매 수량 단위 값"}
    )
    lstn_stcn: str = field(default="", init=False, metadata={"ko": "상장 주수"})
    hts_avls: str = field(default="", init=False, metadata={"ko": "HTS 시가총액"})
    per: str = field(default="", init=False, metadata={"ko": "PER"})
    pbr: str = field(default="", init=False, metadata={"ko": "PBR"})
    stac_month: str = field(default="", init=False, metadata={"ko": "결산 월"})
    vol_tnrt: str = field(default="", init=False, metadata={"ko": "거래량 회전율"})
    eps: str = field(default="", init=False, metadata={"ko": "EPS"})
    bps: str = field(default="", init=False, metadata={"ko": "BPS"})
    d250_hgpr: str = field(default="", init=False, metadata={"ko": "250일 최고가"})
    d250_hgpr_date: str = field(
        default="", init=False, metadata={"ko": "250일 최고가 일자"}
    )
    d250_hgpr_vrss_prpr_rate: str = field(
        default="", init=False, metadata={"ko": "250일 최고가 대비 현재가 비율"}
    )
    d250_lwpr: str = field(default="", init=False, metadata={"ko": "250일 최저가"})
    d250_lwpr_date: str = field(
        default="", init=False, metadata={"ko": "250일 최저가 일자"}
    )
    d250_lwpr_vrss_prpr_rate: str = field(
        default="", init=False, metadata={"ko": "250일 최저가 대비 현재가 비율"}
    )
    stck_dryy_hgpr: str = field(
        default="", init=False, metadata={"ko": "주식 연중 최고가"}
    )
    dryy_hgpr_vrss_prpr_rate: str = field(
        default="", init=False, metadata={"ko": "연중 최고가 대비 현재가 비율"}
    )
    dryy_hgpr_date: str = field(
        default="", init=False, metadata={"ko": "연중 최고가 일자"}
    )
    stck_dryy_lwpr: str = field(
        default="", init=False, metadata={"ko": "주식 연중 최저가"}
    )
    dryy_lwpr_vrss_prpr_rate: str = field(
        default="", init=False, metadata={"ko": "연중 최저가 대비 현재가 비율"}
    )
    dryy_lwpr_date: str = field(
        default="", init=False, metadata={"ko": "연중 최저가 일자"}
    )
    w52_hgpr: str = field(default="", init=False, metadata={"ko": "52주일 최고가"})
    w52_hgpr_vrss_prpr_ctrt: str = field(
        default="", init=False, metadata={"ko": "52주일 최고가 대비 현재가 대비"}
    )
    w52_hgpr_date: str = field(
        default="", init=False, metadata={"ko": "52주일 최고가 일자"}
    )
    w52_lwpr: str = field(default="", init=False, metadata={"ko": "52주일 최저가"})
    w52_lwpr_vrss_prpr_ctrt: str = field(
        default="", init=False, metadata={"ko": "52주일 최저가 대비 현재가 대비"}
    )
    w52_lwpr_date: str = field(
        default="", init=False, metadata={"ko": "52주일 최저가 일자"}
    )
    whol_loan_rmnd_rate: str = field(
        default="", init=False, metadata={"ko": "전체 융자 잔고 비율"}
    )
    ssts_yn: str = field(default="", init=False, metadata={"ko": "공매도가능여부"})
    stck_shrn_iscd: str = field(
        default="", init=False, metadata={"ko": "주식 단축 종목코드"}
    )
    fcam_cnnm: str = field(default="", init=False, metadata={"ko": "액면가 통화명"})
    cpfn_cnnm: str = field(default="", init=False, metadata={"ko": "자본금 통화명"})
    frgn_hldn_qty: str = field(
        default="", init=False, metadata={"ko": "외국인 보유 수량"}
    )
    vi_cls_code: str = field(default="", init=False, metadata={"ko": "VI적용구분코드"})
    ovtm_vi_cls_code: str = field(
        default="", init=False, metadata={"ko": "시간외단일가VI적용구분코드"}
    )
    last_ssts_cntg_qty: str = field(
        default="", init=False, metadata={"ko": "최종 공매도 체결 수량"}
    )
    invt_caful_yn: str = field(default="", init=False, metadata={"ko": "투자유의여부"})
    mrkt_warn_cls_code: str = field(
        default="", init=False, metadata={"ko": "시장경고코드"}
    )
    short_over_yn: str = field(default="", init=False, metadata={"ko": "단기과열여부"})
    sltr_yn: str = field(default="", init=False, metadata={"ko": "정리매매여부"})
    mang_issu_cls_code: str = field(
        default="", init=False, metadata={"ko": "관리종목여부"}
    )

    def __post_init__(self):
        unexpected, missing = self._check_keys()

        self.iscd_stat_cls_code = self.output_raw.get("iscd_stat_cls_code", "")
        self.marg_rate = self.output_raw.get("marg_rate", "")
        self.rprs_mrkt_kor_name = self.output_raw.get("rprs_mrkt_kor_name", "")
        self.bstp_kor_isnm = self.output_raw.get("bstp_kor_isnm", "")
        self.temp_stop_yn = self.output_raw.get("temp_stop_yn", "")
        self.oprc_rang_cont_yn = self.output_raw.get("oprc_rang_cont_yn", "")
        self.clpr_rang_cont_yn = self.output_raw.get("clpr_rang_cont_yn", "")
        self.crdt_able_yn = self.output_raw.get("crdt_able_yn", "")
        self.grmn_rate_cls_code = self.output_raw.get("grmn_rate_cls_code", "")
        self.elw_pblc_yn = self.output_raw.get("elw_pblc_yn", "")
        self.stck_prpr = self.output_raw.get("stck_prpr", "")
        self.prdy_vrss = self.output_raw.get("prdy_vrss", "")
        self.prdy_vrss_sign = self.output_raw.get("prdy_vrss_sign", "")
        self.prdy_ctrt = self.output_raw.get("prdy_ctrt", "")
        self.acml_tr_pbmn = self.output_raw.get("acml_tr_pbmn", "")
        self.acml_vol = self.output_raw.get("acml_vol", "")
        self.prdy_vrss_vol_rate = self.output_raw.get("prdy_vrss_vol_rate", "")
        self.stck_oprc = self.output_raw.get("stck_oprc", "")
        self.stck_hgpr = self.output_raw.get("stck_hgpr", "")
        self.stck_lwpr = self.output_raw.get("stck_lwpr", "")
        self.stck_mxpr = self.output_raw.get("stck_mxpr", "")
        self.stck_llam = self.output_raw.get("stck_llam", "")
        self.stck_sdpr = self.output_raw.get("stck_sdpr", "")
        self.wghn_avrg_stck_prc = self.output_raw.get("wghn_avrg_stck_prc", "")
        self.hts_frgn_ehrt = self.output_raw.get("hts_frgn_ehrt", "")
        self.frgn_ntby_qty = self.output_raw.get("frgn_ntby_qty", "")
        self.pgtr_ntby_qty = self.output_raw.get("pgtr_ntby_qty", "")
        self.pvt_scnd_dmrs_prc = self.output_raw.get("pvt_scnd_dmrs_prc", "")
        self.pvt_frst_dmrs_prc = self.output_raw.get("pvt_frst_dmrs_prc", "")
        self.pvt_pont_val = self.output_raw.get("pvt_pont_val", "")
        self.pvt_frst_dmsp_prc = self.output_raw.get("pvt_frst_dmsp_prc", "")
        self.pvt_scnd_dmsp_prc = self.output_raw.get("pvt_scnd_dmsp_prc", "")
        self.dmrs_val = self.output_raw.get("dmrs_val", "")
        self.dmsp_val = self.output_raw.get("dmsp_val", "")
        self.cpfn = self.output_raw.get("cpfn", "")
        self.rstc_wdth_prc = self.output_raw.get("rstc_wdth_prc", "")
        self.stck_fcam = self.output_raw.get("stck_fcam", "")
        self.stck_sspr = self.output_raw.get("stck_sspr", "")
        self.aspr_unit = self.output_raw.get("aspr_unit", "")
        self.hts_deal_qty_unit_val = self.output_raw.get("hts_deal_qty_unit_val", "")
        self.lstn_stcn = self.output_raw.get("lstn_stcn", "")
        self.hts_avls = self.output_raw.get("hts_avls", "")
        self.per = self.output_raw.get("per", "")
        self.pbr = self.output_raw.get("pbr", "")
        self.stac_month = self.output_raw.get("stac_month", "")
        self.vol_tnrt = self.output_raw.get("vol_tnrt", "")
        self.eps = self.output_raw.get("eps", "")
        self.bps = self.output_raw.get("bps", "")
        self.d250_hgpr = self.output_raw.get("d250_hgpr", "")
        self.d250_hgpr_date = self.output_raw.get("d250_hgpr_date", "")
        self.d250_hgpr_vrss_prpr_rate = self.output_raw.get(
            "d250_hgpr_vrss_prpr_rate", ""
        )
        self.d250_lwpr = self.output_raw.get("d250_lwpr", "")
        self.d250_lwpr_date = self.output_raw.get("d250_lwpr_date", "")
        self.d250_lwpr_vrss_prpr_rate = self.output_raw.get(
            "d250_lwpr_vrss_prpr_rate", ""
        )
        self.stck_dryy_hgpr = self.output_raw.get("stck_dryy_hgpr", "")
        self.dryy_hgpr_vrss_prpr_rate = self.output_raw.get(
            "dryy_hgpr_vrss_prpr_rate", ""
        )
        self.dryy_hgpr_date = self.output_raw.get("dryy_hgpr_date", "")
        self.stck_dryy_lwpr = self.output_raw.get("stck_dryy_lwpr", "")
        self.dryy_lwpr_vrss_prpr_rate = self.output_raw.get(
            "dryy_lwpr_vrss_prpr_rate", ""
        )
        self.dryy_lwpr_date = self.output_raw.get("dryy_lwpr_date", "")
        self.w52_hgpr = self.output_raw.get("w52_hgpr", "")
        self.w52_hgpr_vrss_prpr_ctrt = self.output_raw.get(
            "w52_hgpr_vrss_prpr_ctrt", ""
        )
        self.w52_hgpr_date = self.output_raw.get("w52_hgpr_date", "")
        self.w52_lwpr = self.output_raw.get("w52_lwpr", "")
        self.w52_lwpr_vrss_prpr_ctrt = self.output_raw.get(
            "w52_lwpr_vrss_prpr_ctrt", ""
        )
        self.w52_lwpr_date = self.output_raw.get("w52_lwpr_date", "")
        self.whol_loan_rmnd_rate = self.output_raw.get("whol_loan_rmnd_rate", "")
        self.ssts_yn = self.output_raw.get("ssts_yn", "")
        self.stck_shrn_iscd = self.output_raw.get("stck_shrn_iscd", "")
        self.fcam_cnnm = self.output_raw.get("fcam_cnnm", "")
        self.cpfn_cnnm = self.output_raw.get("cpfn_cnnm", "")
        self.frgn_hldn_qty = self.output_raw.get("frgn_hldn_qty", "")
        self.vi_cls_code = self.output_raw.get("vi_cls_code", "")
        self.ovtm_vi_cls_code = self.output_raw.get("ovtm_vi_cls_code", "")
        self.last_ssts_cntg_qty = self.output_raw.get("last_ssts_cntg_qty", "")
        self.invt_caful_yn = self.output_raw.get("invt_caful_yn", "")
        self.mrkt_warn_cls_code = self.output_raw.get("mrkt_warn_cls_code", "")
        self.short_over_yn = self.output_raw.get("short_over_yn", "")
        self.sltr_yn = self.output_raw.get("sltr_yn", "")
        self.mang_issu_cls_code = self.output_raw.get("mang_issu_cls_code", "")


@dataclass(init=False)
class InquirePriceResponse(BaseRestResponse):
    _endpoint: ClassVar[KISEndpoint] = KISEndpoint.INQUIRE_PRICE_REST
    _output_schema: ClassVar[type[InquirePriceResponseOutput]] = (
        InquirePriceResponseOutput
    )
    output: InquirePriceResponseOutput


@dataclass(kw_only=True)
class InquirePriceRequest(BaseRestRequest):
    """주식현재가 시세[v1_국내주식-008]
    https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/quotations/inquire-price
    """

    _endpoint: ClassVar[KISEndpoint] = KISEndpoint.INQUIRE_PRICE_REST
    _response_spec: ClassVar[type[InquirePriceResponse]] = InquirePriceResponse

    # required query params
    fid_input_iscd: str  # 입력 종목코드; 종목코드 (ex 005930 삼성전자) // ETN은 종목코드 6자리 앞에 Q 입력 필수

    # default query params (can be overridden)
    fid_cond_mrkt_div_code: str = "J"  # 조건 시장 분류 코드; J:KRX, NX:NXT, UN:통합

    def headers(self) -> dict[str, str]:
        """Headers filled by Auth class. Call Auth.get_rest_headers() to populate."""
        return super()._base_headers()

    def query_params(self) -> dict[str, str]:
        return {
            "FID_COND_MRKT_DIV_CODE": self.fid_cond_mrkt_div_code,
            "FID_INPUT_ISCD": self.fid_input_iscd,
        }
