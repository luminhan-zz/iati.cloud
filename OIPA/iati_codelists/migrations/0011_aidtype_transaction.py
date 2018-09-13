# Generated by Django 2.0.6 on 2018-09-12 13:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('iati', '0042_remove_transaction_aid_type'),
        ('iati_codelists', '0010_aidtype_vocabulary'),
    ]

    operations = [
        migrations.AddField(
            model_name='aidtype',
            name='transaction',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='iati.Transaction'),
        ),
    ]