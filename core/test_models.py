from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Company, Obligation, Payment, Transaction


class AccountingModelsTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Example")
        self.obligation = Obligation.objects.create(
            company=self.company, kind=Obligation.Kind.RECEIVABLE,
            counterparty="Customer", amount=Decimal("100.00"),
        )

    def entry(self, amount, company=None, direction=Transaction.Direction.INCOME):
        return Transaction.objects.create(
            company=company or self.company, direction=direction,
            amount=Decimal(amount), date=date(2025, 1, 1),
        )

    def test_partial_payments_and_balance(self):
        Payment.objects.create(obligation=self.obligation, transaction=self.entry("25.10"))
        Payment.objects.create(obligation=self.obligation, transaction=self.entry("74.90"))
        self.assertEqual(self.obligation.paid_amount, Decimal("100.00"))
        self.assertEqual(self.obligation.outstanding_amount, Decimal("0.00"))
        with self.assertRaises(ValidationError):
            Payment.objects.create(obligation=self.obligation, transaction=self.entry("0.01"))

    def test_rejects_other_company_and_wrong_direction(self):
        other = Company.objects.create(name="Other")
        with self.assertRaises(ValidationError):
            Payment.objects.create(obligation=self.obligation, transaction=self.entry("1.00", company=other))
        with self.assertRaises(ValidationError):
            Payment.objects.create(obligation=self.obligation, transaction=self.entry("1.00", direction=Transaction.Direction.EXPENSE))

    def test_payable_requires_expense(self):
        payable = Obligation.objects.create(company=self.company, kind=Obligation.Kind.PAYABLE, counterparty="Supplier", amount=Decimal("10.00"))
        Payment.objects.create(obligation=payable, transaction=self.entry("4.00", direction=Transaction.Direction.EXPENSE))
        self.assertEqual(payable.outstanding_amount, Decimal("6.00"))

    def test_rejects_nonpositive_amounts(self):
        with self.assertRaises(ValidationError):
            self.entry("0.00")
        with self.assertRaises(ValidationError):
            Obligation.objects.create(company=self.company, kind=Obligation.Kind.PAYABLE, counterparty="Supplier", amount=Decimal("-1.00"))

    def test_paid_entries_cannot_be_changed(self):
        entry = self.entry("20.00")
        Payment.objects.create(obligation=self.obligation, transaction=entry)
        entry.amount = Decimal("10.00")
        with self.assertRaises(ValidationError):
            entry.save()
        self.obligation.amount = Decimal("19.00")
        with self.assertRaises(ValidationError):
            self.obligation.save()
