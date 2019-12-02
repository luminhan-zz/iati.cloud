from django.db.models import signals
from django.dispatch import receiver

from geodata.models import Country, Region
from iati_organisation.models import Organisation
from iati_synchroniser.models import Dataset, DatasetNote, Publisher
from solr.codelists.country.tasks import CodeListCountryTaskIndexing
from solr.codelists.region.tasks import CodeListRegionTaskIndexing
from solr.dataset.tasks import DatasetTaskIndexing
from solr.datasetnote.tasks import DatasetNoteTaskIndexing
from solr.organisation.tasks import OrganisationTaskIndexing
from solr.publisher.tasks import PublisherTaskIndexing


@receiver(signals.post_save, sender=Dataset)
def dataset_post_save(sender, instance, **kwargs):
    DatasetTaskIndexing(instance=instance).run()


@receiver(signals.post_save, sender=DatasetNote)
def dataset_note_post_save(sender, instance, **kwargs):
    DatasetNoteTaskIndexing(instance=instance).run()


@receiver(signals.post_save, sender=Publisher)
def publisher_post_save(sender, instance, **kwargs):
    PublisherTaskIndexing(instance=instance).run()


@receiver(signals.post_save, sender=Organisation)
def organisation_post_save(sender, instance, **kwargs):
    OrganisationTaskIndexing(instance=instance).run()


@receiver(signals.post_save, sender=Country)
def code_list_country_post_save(sender, instance, **kwargs):
    CodeListCountryTaskIndexing(instance=instance).run()


@receiver(signals.post_save, sender=Region)
def code_list_region_post_save(sender, instance, **kwargs):
    CodeListRegionTaskIndexing(instance=instance).run()


@receiver(signals.pre_delete, sender=Dataset)
def dataset_pre_delete(sender, instance, **kwargs):
    DatasetTaskIndexing(instance=instance).delete()


@receiver(signals.pre_delete, sender=DatasetNote)
def dataset_note_pre_delete(sender, instance, **kwargs):
    DatasetNoteTaskIndexing(instance=instance).delete()


@receiver(signals.pre_delete, sender=Publisher)
def publisher_pre_delete(sender, instance, **kwargs):
    PublisherTaskIndexing(instance=instance).delete()


@receiver(signals.pre_delete, sender=Organisation)
def organisation_pre_delete(sender, instance, **kwargs):
    OrganisationTaskIndexing(instance=instance).delete()


@receiver(signals.pre_delete, sender=Country)
def code_list_country_pre_delete(sender, instance, **kwargs):
    CodeListCountryTaskIndexing(instance=instance).delete()


@receiver(signals.pre_delete, sender=Region)
def code_list_region_pre_delete(sender, instance, **kwargs):
    CodeListRegionTaskIndexing(instance=instance).delete()
