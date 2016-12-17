# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-10-24 14:51
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('iati_synchroniser', '0014_auto_20161024_1451'),
        ('auth', '0007_alter_validators_add_error_messages'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('iati', '0054_admingroup'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganisationAdminGroup',
            fields=[
                ('group_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='auth.Group')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('publisher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='iati_synchroniser.Publisher', unique=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name_plural': 'Organisation admin groups',
            },
            bases=('auth.group',),
        ),
        migrations.CreateModel(
            name='OrganisationGroup',
            fields=[
                ('group_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='auth.Group')),
                ('publisher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='iati_synchroniser.Publisher', unique=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name_plural': 'Organisation groups',
            },
            bases=('auth.group',),
        ),
        migrations.RemoveField(
            model_name='admingroup',
            name='group_ptr',
        ),
        migrations.RemoveField(
            model_name='admingroup',
            name='owner',
        ),
        migrations.RemoveField(
            model_name='admingroup',
            name='publisher',
        ),
        migrations.DeleteModel(
            name='AdminGroup',
        ),
    ]