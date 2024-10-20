# Generated by Django 5.0.6 on 2024-10-16 19:54

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("PELFCRED", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name="cliente",
            old_name="pais",
            new_name="bairro",
        ),
        migrations.RemoveField(
            model_name="cliente",
            name="ddd",
        ),
        migrations.RemoveField(
            model_name="cliente",
            name="telefone3",
        ),
        migrations.AddField(
            model_name="cliente",
            name="complemento",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="cliente",
            name="status_relatorio",
            field=models.CharField(
                choices=[
                    ("NV", "Novo"),
                    ("R", "Renovado"),
                    ("NG", "Negociado"),
                    ("AC", "Finalizado"),
                ],
                default="Outro",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="cliente",
            name="usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="cliente",
            name="vinculo_telefone2",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="capital_adicional",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="capital_adicional_total",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="capital_inicial",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="data_renovacao",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="dias_semana",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="frequencia",
            field=models.CharField(
                choices=[
                    ("diaria", "Diária"),
                    ("semanal", "Semanal"),
                    ("quinzenal", "Quinzenal"),
                    ("mensal", "Mensal"),
                ],
                default="mensal",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="juros_recebidos",
            field=models.DecimalField(
                decimal_places=2, default=Decimal("0"), max_digits=10
            ),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="numero_parcelas",
            field=models.IntegerField(default=12),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="renovado",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="saldo_devedor",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="total_juros_recebidos",
            field=models.DecimalField(
                decimal_places=2, default=Decimal("0"), max_digits=10
            ),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="total_recebido",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="total_recebido_dinheiro",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="valor_parcelado",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name="emprestimo",
            name="valor_total_calculado",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name="pagamento",
            name="comprovante_pix",
            field=models.ImageField(
                blank=True, null=True, upload_to="comprovantes_pix/"
            ),
        ),
        migrations.AddField(
            model_name="pagamento",
            name="grupo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="auth.group",
            ),
        ),
        migrations.AddField(
            model_name="pagamento",
            name="usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="apelido",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="cep",
            field=models.CharField(blank=True, max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="cpf",
            field=models.CharField(
                error_messages={"unique": "Cpf já cadastrado."},
                max_length=11,
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="nome",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="telefone",
            field=models.CharField(blank=True, max_length=11, null=True),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="telefone2",
            field=models.CharField(blank=True, max_length=11, null=True),
        ),
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
        migrations.AlterField(
            model_name="emprestimo",
            name="taxa_juros",
            field=models.DecimalField(decimal_places=2, max_digits=5),
        ),
        migrations.AlterField(
            model_name="pagamento",
            name="data_pagamento",
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name="pagamento",
            name="emprestimo",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="pagamentos",
                to="PELFCRED.emprestimo",
            ),
        ),
        migrations.AlterField(
            model_name="pagamento",
            name="tipo_pagamento",
            field=models.CharField(
                blank=True,
                choices=[
                    ("pix", "PIX"),
                    ("dinheiro", "Dinheiro"),
                    ("banco_outro", "Banco de Outra Pessoa"),
                ],
                max_length=50,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="pagamento",
            name="valor_pago",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.CreateModel(
            name="ComprovantePIX",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("arquivo", models.ImageField(upload_to="comprovantes_pix/")),
                (
                    "identificador",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("data_upload", models.DateTimeField(auto_now_add=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Parcela",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("data_vencimento", models.DateField()),
                ("pago", models.BooleanField(default=False)),
                ("data_pagamento", models.DateField(blank=True, null=True)),
                (
                    "emprestimo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parcelas_emprestimo",
                        to="PELFCRED.emprestimo",
                    ),
                ),
            ],
        ),
    ]
