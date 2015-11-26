from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from iati.transaction.transaction_manager import TransactionQuerySet
from geodata.models import Country
from geodata.models import Region
from iati_vocabulary.models import RegionVocabulary
from iati_vocabulary.models import SectorVocabulary
from iati_codelists.models import AidType
from iati_codelists.models import DisbursementChannel
from iati_codelists.models import FinanceType
from iati_codelists.models import FlowType
from iati_codelists.models import TiedStatus
from iati_codelists.models import Currency
from iati_codelists.models import Sector
from iati_codelists.models import TransactionType
from iati_organisation.models import Organisation
from iati.models import Activity
from iati.models import Narrative


class Transaction(models.Model):
    activity = models.ForeignKey(Activity)
    aid_type = models.ForeignKey(AidType, null=True, default=None)

    disbursement_channel = models.ForeignKey(
        DisbursementChannel,
        null=True,
        default=None)
    finance_type = models.ForeignKey(FinanceType, null=True, default=None)
    flow_type = models.ForeignKey(FlowType, null=True, default=None)

    tied_status = models.ForeignKey(TiedStatus, null=True, default=None)
    transaction_date = models.DateField(null=True, default=None)
    transaction_type = models.ForeignKey(
        TransactionType,
        null=True,
        default=None)
    value_date = models.DateField(null=True, default=None)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    value_string = models.CharField(max_length=50)
    currency = models.ForeignKey(Currency, null=True, default=None)
    ref = models.CharField(max_length=255, null=True, default="")
    recipient_region = models.ForeignKey(Region, null=True)
    recipient_region_vocabulary = models.ForeignKey(RegionVocabulary, default=1)
    recipient_country = models.ForeignKey(Country, null=True, default=None)

    objects = TransactionQuerySet.as_manager()

    def __unicode__(self, ):
        return "%s: %s - %s" % (self.activity,
                                self.transaction_type,
                                self.transaction_date)


class TransactionProvider(models.Model):
    ref = models.CharField(max_length=250)
    normalized_ref = models.CharField(max_length=120, default="")

    organisation = models.ForeignKey(
        Organisation,
        related_name="transaction_providing_organisation",
        on_delete=models.SET_NULL,
        null=True,
        default=None)
    provider_activity = models.ForeignKey(
        Activity,
        related_name="transaction_provider_activity",
        on_delete=models.SET_NULL,
        null=True,
        default=None)
    provider_activity_ref = models.CharField(db_index=True, max_length=200, null=True, default="")

    transaction = models.OneToOneField(
        Transaction,
        related_name="provider_organisation")

    narratives = GenericRelation(
        Narrative,
        content_type_field='related_content_type',
        object_id_field='related_object_id')

    def __unicode__(self, ):
        return "%s - %s" % (self.ref,
                            self.provider_activity_ref,)


class TransactionReceiver(models.Model):
    ref = models.CharField(max_length=250)
    normalized_ref = models.CharField(max_length=120, default="")

    organisation = models.ForeignKey(
        Organisation,
        related_name="transaction_receiving_organisation",
        on_delete=models.SET_NULL,
        null=True,
        default=None)
    receiver_activity = models.ForeignKey(
        Activity,
        related_name="transaction_receiver_activity",
        on_delete=models.SET_NULL,
        null=True,
        default=None)
    receiver_activity_ref = models.CharField(db_index=True, max_length=200, null=True, default="")

    transaction = models.OneToOneField(
        Transaction,
        related_name="receiver_organisation")

    narratives = GenericRelation(
        Narrative,
        content_type_field='related_content_type',
        object_id_field='related_object_id')

    def __unicode__(self, ):
        return "%s - %s" % (self.ref,
                            self.receiver_activity_ref,)


class TransactionDescription(models.Model):
    transaction = models.OneToOneField(
        Transaction,
        related_name="description")

    narratives = GenericRelation(
        Narrative,
        content_type_field='related_content_type',
        object_id_field='related_object_id')


class TransactionSector(models.Model):
    transaction = models.ForeignKey(Transaction)
    sector = models.ForeignKey(Sector)
    vocabulary = models.ForeignKey(SectorVocabulary)

    def __unicode__(self, ):
        return "%s - %s" % (self.transaction.id, self.sector)


class TransactionRecipientCountry(models.Model):
    transaction = models.ForeignKey(Transaction)
    country = models.ForeignKey(Country)

    def __unicode__(self, ):
        return "%s - %s" % (self.transaction.id, self.country)


class TransactionRecipientRegion(models.Model):
    transaction = models.ForeignKey(Transaction)
    region = models.ForeignKey(Region)
    vocabulary = models.ForeignKey(RegionVocabulary, default=1)

    def __unicode__(self, ):
        return "%s - %s" % (self.transaction.id, self.region)

