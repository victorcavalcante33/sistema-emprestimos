# Generated by Django 5.0.6 on 2024-10-16 05:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("PELFCRED", "0010_emprestimo_capital_adicional_total"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emprestimo",
            name="status",
            field=models.CharField(
                choices=[
                    ("ativo", "Ativo"),
                    ("R", "Renovado"),
                    ("NG", "Negociado"),
                    ("finalizado", "Finalizado"),
                    ("inadimplentes", "Inadimplentes"),
                ],
                default="ativo",
                max_length=20,
            ),
        ),
    ]
