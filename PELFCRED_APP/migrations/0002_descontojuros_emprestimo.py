# Generated by Django 4.2.16 on 2024-11-27 19:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("PELFCRED_APP", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="descontojuros",
            name="emprestimo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="PELFCRED_APP.emprestimo",
            ),
        ),
    ]
