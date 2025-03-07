# Generated by Django 4.2 on 2025-01-01 22:36

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mainapp", "0002_withdraw_alter_transaction_transaction_type_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="deposit",
            options={
                "ordering": ["-timestamp"],
                "verbose_name": "Deposit",
                "verbose_name_plural": "Deposits",
            },
        ),
        migrations.AlterField(
            model_name="deposit",
            name="account_type",
            field=models.CharField(
                blank=True,
                choices=[("spot", "Spot"), ("funding", "Funding")],
                max_length=50,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="deposit",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                ],
                default="pending",
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="deposit",
            name="transaction_fee",
            field=models.DecimalField(
                decimal_places=8, default=Decimal("0.0"), max_digits=10
            ),
        ),
        migrations.AlterField(
            model_name="deposit",
            name="transaction_type",
            field=models.CharField(
                choices=[("deposit", "Deposit"), ("withdrawal", "Withdrawal")],
                max_length=50,
            ),
        ),
    ]
