# Generated by Django 5.0.6 on 2024-11-11 22:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("PELFCRED", "0011_descontojuros"),
    ]

    operations = [
        migrations.AddField(
            model_name="descontojuros",
            name="data_fim",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="descontojuros",
            name="data_inicio",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
