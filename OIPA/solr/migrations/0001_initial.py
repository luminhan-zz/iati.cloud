# Generated by Django 2.0.13 on 2019-10-01 15:36

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityDelete',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_id', models.IntegerField(default=0)),
                ('last_updated_model', models.DateTimeField(auto_now=True, null=True)),
            ],
        ),
    ]