from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce


class Company(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    class Direction(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="transactions")
    direction = models.CharField(max_length=7, choices=Direction.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(amount__gt=0), name="transaction_amount_positive")]

    def save(self, *args, **kwargs):
        if self.pk and Payment.objects.filter(transaction_id=self.pk).exists():
            original = Transaction.objects.get(pk=self.pk)
            if (self.company_id, self.direction, self.amount) != (original.company_id, original.direction, original.amount):
                raise ValidationError("A transaction linked to a payment cannot change company, direction or amount.")
        self.full_clean()
        super().save(*args, **kwargs)


class Obligation(models.Model):
    class Kind(models.TextChoices):
        RECEIVABLE = "receivable", "Receivable"
        PAYABLE = "payable", "Payable"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="obligations")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    counterparty = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(amount__gt=0), name="obligation_amount_positive")]

    @property
    def paid_amount(self):
        return self.payments.aggregate(total=Sum("transaction__amount"))["total"] or Decimal("0.00")

    @property
    def outstanding_amount(self):
        return self.amount - self.paid_amount

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                original = Obligation.objects.select_for_update().get(pk=self.pk)
                if Payment.objects.filter(obligation_id=self.pk).exists():
                    if (self.company_id, self.kind) != (original.company_id, original.kind):
                        raise ValidationError("An obligation with payments cannot change company or kind.")
                    if self.amount < self.paid_amount:
                        raise ValidationError({"amount": "Amount cannot be less than payments already made."})
            self.full_clean()
            super().save(*args, **kwargs)


class Payment(models.Model):
    obligation = models.ForeignKey(Obligation, on_delete=models.PROTECT, related_name="payments")
    transaction = models.OneToOneField(Transaction, on_delete=models.PROTECT, related_name="payment")

    def clean(self):
        super().clean()
        if not self.obligation_id or not self.transaction_id:
            return
        obligation = self.obligation
        entry = self.transaction
        if obligation.company_id != entry.company_id:
            raise ValidationError("Payment and obligation must belong to the same company.")
        expected = Transaction.Direction.INCOME if obligation.kind == Obligation.Kind.RECEIVABLE else Transaction.Direction.EXPENSE
        if entry.direction != expected:
            raise ValidationError("Transaction direction does not match the obligation kind.")
        already_paid = obligation.payments.exclude(pk=self.pk).aggregate(total=Sum("transaction__amount"))["total"] or Decimal("0.00")
        if already_paid + entry.amount > obligation.amount:
            raise ValidationError("Payment exceeds the outstanding amount.")

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                previous = Payment.objects.get(pk=self.pk)
                if previous.obligation_id != self.obligation_id or previous.transaction_id != self.transaction_id:
                    raise ValidationError("A payment's obligation and transaction cannot be changed; delete and recreate it.")
            # Serialize payments and obligation edits for the same obligation.
            self.obligation = Obligation.objects.select_for_update().get(pk=self.obligation_id)
            self.transaction = Transaction.objects.select_for_update().get(pk=self.transaction_id)
            self.full_clean()
            super().save(*args, **kwargs)
