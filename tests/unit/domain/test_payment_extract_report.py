import pytest

from app.domain.payment_extract_report import (
    PaymentLineClassification,
    PaymentLineType,
    UnclassifiablePaymentLineError,
    classify_payment_line,
)
from app.models.claim.enums import InvoiceTypeCode, POAType

PROFIT_COSTS = PaymentLineClassification("Profit costs", "Profit costs")
POA_PROFIT_COSTS = PaymentLineClassification("Profit costs (80%)", "Profit costs")
DISBURSEMENTS = PaymentLineClassification("Expert costs", "Disbursements")


class TestClassifyPaymentLine:
    @pytest.mark.parametrize(
        ("invoice_type", "expected"),
        [
            (InvoiceTypeCode.FINAL_BILL_FEES, PROFIT_COSTS),
            (InvoiceTypeCode.FINAL_BILL_DISBURSEMENT, DISBURSEMENTS),
        ],
    )
    def test_final_bill_lines_are_classified_by_invoice_type(
        self, invoice_type, expected
    ):
        line_type = PaymentLineType(invoice_type=invoice_type)

        assert classify_payment_line(line_type) == expected

    @pytest.mark.parametrize(
        ("poa_type", "expected"),
        [
            (POAType.PROFIT_COST, POA_PROFIT_COSTS),
            (POAType.EXPERT_COST, DISBURSEMENTS),
            (POAType.NON_EXPERT_DISBURSEMENT, DISBURSEMENTS),
        ],
    )
    def test_poa_lines_are_classified_by_claim_poa_type(self, poa_type, expected):
        line_type = PaymentLineType(invoice_type=InvoiceTypeCode.POA, poa_type=poa_type)

        assert classify_payment_line(line_type) == expected

    @pytest.mark.parametrize(
        ("original_poa_type", "expected"),
        [
            (POAType.PROFIT_COST, POA_PROFIT_COSTS),
            (POAType.EXPERT_COST, DISBURSEMENTS),
            (POAType.NON_EXPERT_DISBURSEMENT, DISBURSEMENTS),
        ],
    )
    def test_recouped_lines_are_classified_by_original_poa_type(
        self, original_poa_type, expected
    ):
        line_type = PaymentLineType(
            invoice_type=InvoiceTypeCode.RECOUPED,
            original_poa_type=original_poa_type,
        )

        assert classify_payment_line(line_type) == expected

    def test_recouped_line_ignores_its_own_claim_poa_type(self):
        line_type = PaymentLineType(
            invoice_type=InvoiceTypeCode.RECOUPED,
            poa_type=POAType.EXPERT_COST,
            original_poa_type=POAType.PROFIT_COST,
        )

        assert classify_payment_line(line_type) == POA_PROFIT_COSTS

    def test_raises_when_poa_line_has_no_poa_type(self):
        line_type = PaymentLineType(invoice_type=InvoiceTypeCode.POA)

        with pytest.raises(UnclassifiablePaymentLineError):
            classify_payment_line(line_type)

    def test_raises_when_recouped_line_has_no_original_poa_type(self):
        line_type = PaymentLineType(
            invoice_type=InvoiceTypeCode.RECOUPED, poa_type=POAType.PROFIT_COST
        )

        with pytest.raises(UnclassifiablePaymentLineError):
            classify_payment_line(line_type)
