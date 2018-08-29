# Generated by Django 2.0.6 on 2018-07-26 15:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('iati', '0016_resultindicator_aggregation_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='result_indicator_baseline',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='baseline_locations', to='iati.ResultIndicator'),
        ),
    ]