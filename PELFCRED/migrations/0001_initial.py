# Generated by Django 5.0.6 on 2024-08-15 19:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Cliente",
            fields=[
                (
                    "cpf",
                    models.CharField(max_length=11, primary_key=True, serialize=False),
                ),
                ("nome", models.CharField(blank=True, max_length=200, null=True)),
                ("documento", models.CharField(blank=True, max_length=20, null=True)),
                ("cnpj", models.CharField(blank=True, max_length=14, null=True)),
                ("ddd", models.CharField(blank=True, max_length=3, null=True)),
                ("telefone", models.CharField(blank=True, max_length=9, null=True)),
                ("telefone2", models.CharField(blank=True, max_length=9, null=True)),
                ("telefone3", models.CharField(blank=True, max_length=9, null=True)),
                ("apelido", models.CharField(blank=True, max_length=100, null=True)),
                ("endereco", models.CharField(blank=True, max_length=200, null=True)),
                (
                    "numero_endereco",
                    models.CharField(blank=True, max_length=10, null=True),
                ),
                ("cep", models.CharField(blank=True, max_length=9, null=True)),
                ("pais", models.CharField(blank=True, max_length=100, null=True)),
                ("uf", models.CharField(blank=True, max_length=2, null=True)),
                ("cidade", models.CharField(blank=True, max_length=100, null=True)),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                ("bloqueado", models.BooleanField(default=False)),
                ("data_registro", models.DateTimeField(auto_now_add=True)),
                (
                    "grupo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="auth.group",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Emprestimo",
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
                ("valor_total", models.DecimalField(decimal_places=2, max_digits=10)),
                ("capital", models.DecimalField(decimal_places=2, max_digits=10)),
                ("taxa_juros", models.FloatField()),
                ("data_inicio", models.DateField()),
                ("data_vencimento", models.DateField()),
                ("status", models.CharField(max_length=50)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="PELFCRED.cliente",
                    ),
                ),
                (
                    "grupo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="auth.group",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Pagamento",
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
                ("data_pagamento", models.DateField()),
                ("valor_pago", models.DecimalField(decimal_places=2, max_digits=10)),
                ("tipo_pagamento", models.CharField(max_length=50)),
                ("cpf_pagador", models.CharField(blank=True, max_length=11, null=True)),
                (
                    "nome_pagador",
                    models.CharField(blank=True, max_length=200, null=True),
                ),
                (
                    "emprestimo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="PELFCRED.emprestimo",
                    ),
                ),
            ],
        ),
    ]
