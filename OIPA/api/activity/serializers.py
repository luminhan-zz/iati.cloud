from collections import OrderedDict

from django.db.models import Sum
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SkipField
from rest_framework.relations import PKOnlyObject
from rest_framework.reverse import reverse

from api.activity.filters import RelatedActivityFilter
from api.codelist.serializers import (
    AidTypeSerializer, CodelistSerializer, NarrativeContainerSerializer,
    NarrativeSerializer, OrganisationNarrativeSerializer, VocabularySerializer
)
from api.country.serializers import CountrySerializer
from api.dataset.serializers import SimpleDatasetSerializer
from api.generics.fields import PointField
from api.generics.serializers import (
    DynamicFieldsModelSerializer, DynamicFieldsSerializer,
    ModelSerializerNoValidation, SerializerNoValidation
)
from api.generics.utils import get_or_none, get_or_raise, handle_errors
from api.publisher.serializers import PublisherSerializer
from api.region.serializers import BasicRegionSerializer
from api.sector.serializers import SectorSerializer
from iati.models import (
    Activity, ActivityDate, ActivityDefaultAidType,
    ActivityParticipatingOrganisation, ActivityPolicyMarker,
    ActivityRecipientCountry, ActivityRecipientRegion,
    ActivityReportingOrganisation, ActivitySector, ActivityTag, Budget,
    BudgetItem, BudgetItemDescription, Condition, Conditions, ContactInfo,
    ContactInfoDepartment, ContactInfoJobTitle, ContactInfoMailingAddress,
    ContactInfoOrganisation, ContactInfoPersonName, CountryBudgetItem, CrsAdd,
    CrsAddLoanStatus, CrsAddLoanTerms, CrsAddOtherFlags, Description,
    DocumentLink, DocumentLinkCategory, DocumentLinkLanguage,
    DocumentLinkTitle, Fss, FssForecast, HumanitarianScope, LegacyData,
    Location, LocationActivityDescription, LocationAdministrative,
    LocationDescription, LocationName, NameSpaceElement, Narrative,
    Organisation, OtherIdentifier, PlannedDisbursement,
    PlannedDisbursementProvider, PlannedDisbursementReceiver, RelatedActivity,
    Result, ResultDescription, ResultIndicator, ResultIndicatorBaseline,
    ResultIndicatorBaselineDimension, ResultIndicatorDescription,
    ResultIndicatorPeriod, ResultIndicatorPeriodActualDimension,
    ResultIndicatorPeriodActualLocation, ResultIndicatorPeriodTarget,
    ResultIndicatorPeriodTargetDimension, ResultIndicatorPeriodTargetLocation,
    ResultIndicatorReference, ResultIndicatorTitle, ResultReference,
    ResultTitle, ResultType, Title
)
from iati.parser import validators
from iati.transaction.models import (
    Transaction, TransactionAidType, TransactionDescription,
    TransactionProvider, TransactionReceiver, TransactionRecipientCountry,
    TransactionRecipientRegion, TransactionSector
)
from iati_organisation import models as organisation_models


def save_narratives(instance, data, activity_instance):
    current_narratives = instance.narratives.all()

    current_ids = set([i.id for i in current_narratives])
    old_ids = set(filter(lambda x: x is not None, [i.get('id') for i in data]))
    new_data = filter(lambda x: x.get('id') is None, data)

    to_remove = list(current_ids.difference(old_ids))
    to_add = new_data
    to_update = list(current_ids.intersection(old_ids))

    for fk_id in to_update:
        narrative = Narrative.objects.get(pk=fk_id)
        narrative_data = filter(lambda x: x['id'] is fk_id, data)[0]

        for field, data in narrative_data.items():
            setattr(narrative, field, data)
        narrative.save()

    for fk_id in to_remove:
        narrative = Narrative.objects.get(pk=fk_id)
        narrative.delete()

    for narrative_data in to_add:

        Narrative.objects.create(
            related_object=instance,
            activity=activity_instance,
            **narrative_data)


class ValueSerializer(SerializerNoValidation):
    currency = CodelistSerializer()
    date = serializers.CharField(source='value_date')
    value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False,
    )

    class Meta:
        fields = (
            'value',
            'date',
            'currency',
        )


class DocumentLinkCategorySerializer(ModelSerializerNoValidation):
    category = CodelistSerializer()

    document_link = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='DocumentLinkCategory')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = DocumentLinkCategory
        fields = (
            'document_link',
            'id',
            'category',
            'name_space',
        )

    def validate(self, data):
        document_link = get_or_raise(
            DocumentLink,
            data,
            'document_link'
        )

        validated = validators.document_link_category(
            document_link,
            data.get('category', {}).get('code'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        document_link = validated_data.get('document_link')

        instance = DocumentLinkCategory.objects.create(
            **validated_data
        )

        document_link.activity.modified = True
        document_link.activity.save()

        return instance

    def update(self, instance, validated_data):
        document_link = validated_data.get('document_link')

        update_instance = DocumentLinkCategory(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        document_link.activity.modified = True
        document_link.activity.save()

        return update_instance


class DocumentLinkLanguageSerializer(ModelSerializerNoValidation):
    language = CodelistSerializer()
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='DocumentLinkLanguage')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    document_link = serializers.CharField(write_only=True)

    class Meta:
        model = DocumentLinkLanguage
        fields = (
            'document_link',
            'id',
            'language',
            'name_space',
        )

    def validate(self, data):
        document_link = get_or_raise(
            DocumentLink,
            data, 'document_link'
        )

        validated = validators.document_link_language(
            document_link,
            data.get('language', {}).get('code'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        document_link = validated_data.get('document_link')

        instance = DocumentLinkLanguage.objects.create(
            **validated_data
        )

        document_link.activity.modified = True
        document_link.activity.save()

        return instance

    def update(self, instance, validated_data):
        document_link = validated_data.get('document_link')

        update_instance = DocumentLinkLanguage(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        document_link.activity.modified = True
        document_link.activity.save()

        return update_instance


class DocumentLinkSerializer(ModelSerializerNoValidation):

    class DocumentDateSerializer(SerializerNoValidation):
        # CharField because we want to let the validators do the parsing
        iso_date = serializers.CharField()

    format = CodelistSerializer(source='file_format')
    categories = DocumentLinkCategorySerializer(
        many=True, required=False, source="documentlinkcategory_set")
    languages = DocumentLinkLanguageSerializer(
        many=True, required=False, source="documentlinklanguage_set")
    title = NarrativeContainerSerializer(source="documentlinktitle")
    document_date = DocumentDateSerializer(source="*")

    activity = serializers.CharField(write_only=True)

    description = NarrativeContainerSerializer(
        source='documentlinkdescription'
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='DocumentLink')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = DocumentLink
        fields = (
            'activity',
            'id',
            'url',
            'format',
            'categories',
            'languages',
            'title',
            'document_date',
            'description',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_document_link(
            activity,
            data.get('url'),
            data.get('file_format', {}).get('code'),
            data.get('iso_date'),
            data.get('documentlinktitle', {}).get('narratives'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')
        title_narratives_data = validated_data.pop('title_narratives', [])

        instance = DocumentLink.objects.create(**validated_data)

        document_link_title = DocumentLinkTitle.objects.create(
            document_link=instance
        )

        save_narratives(document_link_title, title_narratives_data, activity)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')
        title_narratives_data = validated_data.pop('title_narratives', [])

        update_instance = DocumentLink(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        save_narratives(
            update_instance.documentlinktitle,
            title_narratives_data,
            activity
        )

        activity.modified = True
        activity.save()

        return update_instance


class CapitalSpendSerializer(ModelSerializerNoValidation):
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=False,
        source="*"
    )

    class Meta:
        model = Activity
        fields = ('percentage',)


class BudgetSerializer(ModelSerializerNoValidation):

    value = ValueSerializer(source='*')
    type = CodelistSerializer()
    status = CodelistSerializer()

    activity = serializers.CharField(write_only=True)

    # because we want to validate in the validator instead
    period_start = serializers.CharField()
    period_end = serializers.CharField()

    activity_id = serializers.CharField(
        source='activity.iati_identifier',
        read_only=True
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='Budget')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = Budget
        # filter_class = BudgetFilter
        fields = (
            'activity',
            'id',
            'type',
            'status',
            'period_start',
            'period_end',
            'value',
            # TODO: update test (if it exists):
            'xdr_value',
            'usd_value',
            'eur_value',
            'gbp_value',
            'jpy_value',
            'cad_value',
            'activity_id',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_budget(
            activity,
            data.get('type', {}).get('code'),
            data.get('status', {}).get('code'),
            data.get('period_start'),
            data.get('period_end'),
            data.get('value'),
            data.get('currency').get('code'),
            data.get('value_date'),

        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')

        instance = Budget.objects.create(**validated_data)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')

        update_instance = Budget(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance


class PlannedDisbursementProviderSerializer(ModelSerializerNoValidation):
    ref = serializers.CharField(source="normalized_ref")
    organisation = serializers.PrimaryKeyRelatedField(
        queryset=Organisation.objects.all(), required=False)
    type = CodelistSerializer()
    provider_activity = serializers.PrimaryKeyRelatedField(
        queryset=Activity.objects.all(), required=False)
    narratives = NarrativeSerializer(many=True, required=False)

    class Meta:
        model = PlannedDisbursementProvider

        fields = (
            'ref',
            'organisation',
            'type',
            'provider_activity',
            'narratives',
        )

        validators = []


class PlannedDisbursementReceiverSerializer(ModelSerializerNoValidation):
    ref = serializers.CharField(source="normalized_ref")
    organisation = serializers.PrimaryKeyRelatedField(
        queryset=Organisation.objects.all(), required=False)
    type = CodelistSerializer()
    receiver_activity = serializers.PrimaryKeyRelatedField(
        queryset=Activity.objects.all(), required=False)
    narratives = NarrativeSerializer(many=True, required=False)

    class Meta:
        model = PlannedDisbursementReceiver

        fields = (
            'ref',
            'organisation',
            'type',
            'receiver_activity',
            'narratives',
        )

        validators = []


class PlannedDisbursementSerializer(ModelSerializerNoValidation):
    value = ValueSerializer(source='*')
    type = CodelistSerializer()

    activity = serializers.CharField(write_only=True)

    period_start = serializers.CharField()
    period_end = serializers.CharField()

    provider_organisation = PlannedDisbursementProviderSerializer(
        required=False
    )
    receiver_organisation = PlannedDisbursementReceiverSerializer(
        required=False
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='PlannedDisbursement')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = PlannedDisbursement

        fields = (
            'activity',
            'id',
            'type',
            'period_start',
            'period_end',
            'value',
            'provider_organisation',
            'receiver_organisation',
            'name_space',
        )

        validators = []

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_planned_disbursement(
            activity,
            data.get('type', {}).get('code'),
            data.get('period_start'),
            data.get('period_end'),
            data.get('currency', {}).get('code'),
            data.get('value_date'),
            data.get('value'),
            data.get('provider_organisation', {}).get('normalized_ref'),
            data.get('provider_organisation', {}).get('provider_activity'),
            data.get('provider_organisation', {}).get('type', {}).get('code'),
            data.get('provider_organisation', {}).get('narratives'),
            data.get('receiver_organisation', {}).get('normalized_ref'),
            data.get('receiver_organisation', {}).get('receiver_activity'),
            data.get('receiver_organisation', {}).get('type', {}).get('code'),
            data.get('receiver_organisation', {}).get('narratives'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')
        provider_data = validated_data.pop('provider_org')
        provider_narratives_data = validated_data.pop(
            'provider_org_narratives',
            []
        )
        receiver_data = validated_data.pop('receiver_org')
        receiver_narratives_data = validated_data.pop(
            'receiver_org_narratives',
            []
        )

        instance = PlannedDisbursement.objects.create(
            **validated_data
        )

        if provider_data['ref']:
            provider_org = PlannedDisbursementProvider.objects.create(
                planned_disbursement=instance,
                **provider_data
            )
            save_narratives(provider_org, provider_narratives_data, activity)
            validated_data['provider_organisation'] = provider_org
        if receiver_data['ref']:
            receiver_org = PlannedDisbursementReceiver.objects.create(
                planned_disbursement=instance,
                **receiver_data
            )
            save_narratives(receiver_org, receiver_narratives_data, activity)
            validated_data['receiver_organisation'] = receiver_org

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')
        provider_data = validated_data.pop('provider_org')
        provider_narratives_data = validated_data.pop(
            'provider_org_narratives',
            []
        )
        receiver_data = validated_data.pop('receiver_org')
        receiver_narratives_data = validated_data.pop(
            'receiver_org_narratives',
            []
        )

        update_instance = PlannedDisbursement(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        # TODO: don't create here, but update? - 2016-12-12
        if provider_data['ref']:
            provider_org, created = PlannedDisbursementProvider.objects.update_or_create(  # NOQA: E501
                planned_disbursement=instance, defaults=provider_data)
            save_narratives(provider_org, provider_narratives_data, activity)
            validated_data['provider_organisation'] = provider_org
        if receiver_data['ref']:
            receiver_org, created = PlannedDisbursementReceiver.objects.update_or_create(  # NOQA: E501
                planned_disbursement=instance, defaults=receiver_data)
            save_narratives(receiver_org, receiver_narratives_data, activity)
            validated_data['receiver_organisation'] = receiver_org

        activity.modified = True
        activity.save()

        return update_instance


class ActivityDateSerializer(ModelSerializerNoValidation):
    type = CodelistSerializer()
    iso_date = serializers.DateField()
    narratives = NarrativeSerializer(many=True)
    activity = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ActivityDate')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_activity_date(
            activity,
            data.get('type', {}).get('code'),
            data.get('iso_date'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')

        instance = ActivityDate.objects.create(**validated_data)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')

        update_instance = ActivityDate(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance

    class Meta:
        model = ActivityDate
        fields = (
            'id',
            'activity',
            'iso_date',
            'type',
            'narratives',
            'name_space'
        )


class ActivityAggregationSerializer(DynamicFieldsSerializer):
    budget_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    budget_currency = serializers.CharField()
    disbursement_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    disbursement_currency = serializers.CharField()
    incoming_funds_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    incoming_funds_currency = serializers.CharField()
    commitment_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    commitment_currency = serializers.CharField()
    expenditure_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    expenditure_currency = serializers.CharField()

    interest_payment_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    interest_payment_currency = serializers.CharField()

    loan_repayment_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    loan_repayment_currency = serializers.CharField()

    reimbursement_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    reimbursement_currency = serializers.CharField()

    purchase_of_equity_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    purchase_of_equity_currency = serializers.CharField()

    sale_of_equity_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    sale_of_equity_currency = serializers.CharField()

    credit_guarantee_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    credit_guarantee_currency = serializers.CharField()

    incoming_commitment_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        coerce_to_string=False)
    incoming_commitment_currency = serializers.CharField()


class CustomReportingOrganisationURLSerializer(
        serializers.HyperlinkedIdentityField):
    """A custom serializer to allow to use different argument for
       HyperlinkedIdentityField for ReportingOrganisation serializer
    """

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'pk': obj.publisher.organisation.organisation_identifier
        }
        return reverse(
            view_name, kwargs=url_kwargs, request=request, format=format)


class ReportingOrganisationSerializer(DynamicFieldsModelSerializer):
    # TODO: Link to organisation standard (hyperlinked)
    ref = serializers.CharField(
        source="publisher.organisation.organisation_identifier"
    )
    url = CustomReportingOrganisationURLSerializer(
        view_name='organisations:organisation-detail',
    )
    type = CodelistSerializer(source="publisher.organisation.type")
    secondary_reporter = serializers.BooleanField(required=False)

    activity = serializers.CharField(write_only=True)

    narratives = OrganisationNarrativeSerializer(
        source="publisher.organisation.name.narratives",
        many=True,
        required=False
    )

    class Meta:
        model = organisation_models.Organisation
        fields = (
            'id',
            'ref',
            'url',
            'type',
            'secondary_reporter',
            'narratives',
            'activity',
        )


class CustomReportingOrganisationDataURLSerializer(
        serializers.HyperlinkedIdentityField):
    """A custom serializer to allow to use different argument for
       HyperlinkedIdentityField for ReportingOrganisation serializer
    """

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'pk': obj.organisation.organisation_identifier
        }
        return reverse(
            view_name, kwargs=url_kwargs, request=request, format=format)


class ReportingOrganisationDataSerializer(DynamicFieldsModelSerializer):  # NOQA: E501
    """
    Why the is ReportingOrganisationDataSerializer
    Because this class is directly to data of Reporting Organisation data
    Otherwise ReportingOrganisationSerializer is using a publisher data
    """
    ref = serializers.CharField()
    url = CustomReportingOrganisationDataURLSerializer(
        view_name='organisations:organisation-detail',
    )
    type = CodelistSerializer()
    secondary_reporter = serializers.BooleanField(required=False)

    activity = serializers.CharField(write_only=True, required=True)

    # TODO: please check this why in narrative in Reporting org is empty
    # So to get narratives should be from organisation
    narratives = OrganisationNarrativeSerializer(
        source="organisation.name.narratives",
        many=True,
        required=False
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ActivityReportingOrganisation')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ActivityReportingOrganisation
        fields = (
            'id',
            'ref',
            'url',
            'type',
            'secondary_reporter',
            'narratives',
            'name_space',
            'activity',
        )


class ParticipatingOrganisationSerializer(ModelSerializerNoValidation):
    # TODO: Link to organisation standard (hyperlinked)
    ref = serializers.CharField(source='normalized_ref')
    type = CodelistSerializer()
    role = CodelistSerializer()
    activity_id = serializers.CharField(
        source='org_activity_id',
        required=False
    )
    narratives = NarrativeSerializer(many=True, required=False)

    activity = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)
    crs_channel_code = CodelistSerializer()

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ActivityParticipatingOrganisation')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_participating_org(
            activity,
            data.get('normalized_ref'),
            data.get('type', {}).get('code'),
            data.get('role', {}).get('code'),
            data.get('activity_id'),
            data.get('narratives')
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')
        narratives = validated_data.pop('narratives', [])

        instance = ActivityParticipatingOrganisation.objects.create(
            **validated_data
        )

        save_narratives(instance, narratives, activity)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')
        narratives = validated_data.pop('narratives', [])

        update_instance = ActivityParticipatingOrganisation(
            **validated_data
        )
        update_instance.id = instance.id
        update_instance.save()

        save_narratives(instance, narratives, activity)

        activity.modified = True
        activity.save()

        return update_instance

    class Meta:
        model = ActivityParticipatingOrganisation
        fields = (
            'id',
            'ref',
            'type',
            'role',
            'activity_id',
            'activity',
            'narratives',
            'name_space',
            'crs_channel_code',
        )


class OtherIdentifierSerializer(ModelSerializerNoValidation):
    class OwnerOrgSerializer(SerializerNoValidation):
        ref = serializers.CharField(source='owner_ref')
        narratives = NarrativeSerializer(many=True, required=False)

    ref = serializers.CharField(source="identifier")
    type = CodelistSerializer()

    owner_org = OwnerOrgSerializer(source="*")

    activity = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='OtherIdentifier')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = OtherIdentifier
        fields = (
            'id',
            'activity',
            'ref',
            'type',
            'owner_org',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.other_identifier(
            activity,
            data.get('identifier'),
            data.get('type', {}).get('code'),
            data.get('owner_ref'),
            data.get('narratives'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')
        narratives = validated_data.pop('narratives', [])

        instance = OtherIdentifier.objects.create(**validated_data)

        save_narratives(instance, narratives, activity)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')
        narratives = validated_data.pop('narratives', [])

        update_instance = OtherIdentifier(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        save_narratives(instance, narratives, activity)

        activity.modified = True
        activity.save()

        return update_instance


class ActivityPolicyMarkerSerializer(ModelSerializerNoValidation):
    vocabulary = VocabularySerializer()
    vocabulary_uri = serializers.URLField()
    policy_marker = CodelistSerializer(source="code")
    significance = CodelistSerializer()
    narratives = NarrativeSerializer(many=True)

    activity = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ActivityPolicyMarker')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_policy_marker(
            activity,
            data.get('vocabulary', {}).get('code'),
            data.get('vocabulary_uri'),
            data.get('code', {}).get('code'),
            data.get('significance', {}).get('code'),
            data.get('narratives')
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')
        narratives = validated_data.pop('narratives', [])

        instance = ActivityPolicyMarker.objects.create(
            **validated_data
        )

        save_narratives(instance, narratives, activity)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')
        narratives = validated_data.pop('narratives', [])

        update_instance = ActivityPolicyMarker(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        save_narratives(update_instance, narratives, activity)

        activity.modified = True
        activity.save()

        return update_instance

    class Meta:
        model = ActivityPolicyMarker
        fields = (
            'activity',
            'id',
            'vocabulary',
            'vocabulary_uri',
            'policy_marker',
            'significance',
            'narratives',
            'name_space',
        )


# TODO: change to NarrativeContainer
class TitleSerializer(ModelSerializerNoValidation):
    narratives = NarrativeSerializer(many=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='Title')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = Title
        fields = ('id', 'narratives', 'name_space')


class DescriptionSerializer(ModelSerializerNoValidation):
    type = CodelistSerializer()
    narratives = NarrativeSerializer(many=True)

    activity = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='Description')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_description(
            activity,
            data.get('type', {}).get('code'),
            data.get('narratives')
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')
        narratives = validated_data.pop('narratives', [])

        instance = Description.objects.create(**validated_data)

        save_narratives(instance, narratives, activity)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')
        narratives = validated_data.pop('narratives', [])

        update_instance = Description(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        save_narratives(update_instance, narratives, activity)

        activity.modified = True
        activity.save()

        return update_instance

    class Meta:
        model = Description
        fields = (
            'id',
            'type',
            'narratives',
            'activity',
            'name_space',
        )


class RelatedActivitySerializer(ModelSerializerNoValidation):
    ref_activity = serializers.HyperlinkedRelatedField(
        view_name='activities:activity-detail', read_only=True)
    type = CodelistSerializer()
    ref_activity_id = serializers.CharField(
        read_only=True,
        source="ref_activity.id"
    )
    activity = serializers.CharField(
        write_only=True,
        source="current_activity"
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='RelatedActivity')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = RelatedActivity
        filter_class = RelatedActivityFilter
        fields = (
            'activity',
            'id',
            'ref_activity',
            'ref_activity_id',
            'ref',
            'type',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'current_activity')

        validated = validators.related_activity(
            activity,
            data.get('ref'),
            data.get('type', {}).get('code'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('current_activity')

        instance = RelatedActivity.objects.create(**validated_data)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('current_activity')

        update_instance = RelatedActivity(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance


class LegacyDataSerializer(ModelSerializerNoValidation):
    activity = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='LegacyData')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = LegacyData
        fields = (
            'id',
            'activity',
            'name',
            'value',
            'iati_equivalent',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.legacy_data(
            activity,
            data.get('name'),
            data.get('value'),
            data.get('iati_equivalent'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')

        instance = LegacyData.objects.create(**validated_data)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')

        update_instance = LegacyData(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance


class ActivitySectorSerializer(ModelSerializerNoValidation):
    sector = SectorSerializer(fields=('url', 'code', 'name'))
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=False
    )
    vocabulary = VocabularySerializer()
    vocabulary_uri = serializers.URLField()

    activity = serializers.CharField(write_only=True)
    narratives = NarrativeSerializer(many=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ActivitySector')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ActivitySector
        fields = (
            'activity',
            'id',
            'sector',
            'percentage',
            'vocabulary',
            'vocabulary_uri',
            'narratives',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity__sector(
            activity,
            data.get('sector', {}).get('code'),
            data.get('vocabulary', {}).get('code'),
            data.get('vocabulary_uri'),
            data.get('percentage'),
            getattr(self, 'instance', None),  # only on update
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')

        instance = ActivitySector.objects.create(**validated_data)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')

        update_instance = ActivitySector(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance


class BudgetItemSerializer(ModelSerializerNoValidation):

    class BudgetItemDescriptionSerializer(SerializerNoValidation):
        narratives = NarrativeSerializer(many=True, required=False)

    budget_identifier = CodelistSerializer(source="code")
    description = BudgetItemDescriptionSerializer(required=False)

    country_budget_item = serializers.CharField(write_only=True)

    class Meta:
        model = BudgetItem
        fields = (
            'id',
            'country_budget_item',
            'budget_identifier',
            'description',
        )

    def validate(self, data):
        country_budget_item = get_or_raise(
            CountryBudgetItem, data, 'country_budget_item')

        validated = validators.budget_item(
            country_budget_item,
            data.get('code', {}).get('code'),
            data.get('description', {}).get('narratives', [])
        )

        return handle_errors(validated)

    def create(self, validated_data):
        country_budget_item = validated_data.get('country_budget_item')
        narratives = validated_data.pop('narratives', [])

        instance = BudgetItem.objects.create(**validated_data)

        description = BudgetItemDescription.objects.create(
            budget_item=instance
        )

        save_narratives(description, narratives, country_budget_item.activity)

        country_budget_item.activity.modified = True
        country_budget_item.activity.save()

        return instance

    def update(self, instance, validated_data):
        country_budget_item = validated_data.get('country_budget_item', [])
        narratives = validated_data.pop('narratives', [])

        update_instance = BudgetItem(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        save_narratives(
            instance.description,
            narratives,
            country_budget_item.activity
        )

        country_budget_item.activity.modified = True
        country_budget_item.activity.save()

        return update_instance


class CountryBudgetItemsSerializer(ModelSerializerNoValidation):

    vocabulary = VocabularySerializer()

    activity = serializers.CharField(write_only=True)

    budget_items = BudgetItemSerializer(
        many=True,
        source='budgetitem_set',
        read_only=True,
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='CountryBudgetItem')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = CountryBudgetItem
        fields = (
            'id',
            'activity',
            'vocabulary',
            'budget_items',
            'name_space'
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.country_budget_items(
            activity,
            data.get('vocabulary', {}).get('code'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')

        instance = CountryBudgetItem.objects.create(
            **validated_data
        )

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')

        update_instance = CountryBudgetItem(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance

    def destroy(self, *args, **kwargs):
        activity = Activity.objects.get(pk=kwargs.get('pk'))
        activity.country_budget_items.delete()

        activity.modified = True
        activity.save()


class ConditionSerializer(ModelSerializerNoValidation):

    type = CodelistSerializer()
    narratives = NarrativeSerializer(many=True, required=False)

    conditions = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='Condition')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = Condition
        fields = (
            'id',
            'conditions',
            'type',
            'narratives',
            'name_space',
        )

    def validate(self, data):
        conditions = get_or_raise(Conditions, data, 'conditions')

        validated = validators.condition(
            conditions,
            data.get('type', {}).get('code'),
            data.get('narratives', [])
        )

        return handle_errors(validated)

    def create(self, validated_data):
        conditions = validated_data.get('conditions')
        narratives = validated_data.pop('narratives', [])

        instance = Condition.objects.create(**validated_data)

        save_narratives(instance, narratives, conditions.activity)

        conditions.activity.modified = True
        conditions.activity.save()

        return instance

    def update(self, instance, validated_data):
        conditions = validated_data.get('conditions', [])
        narratives = validated_data.pop('narratives', [])

        update_instance = Condition(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        save_narratives(instance, narratives, conditions.activity)

        conditions.activity.modified = True
        conditions.activity.save()

        return update_instance


class ConditionsSerializer(ModelSerializerNoValidation):
    condition = ConditionSerializer(
        many=True,
        read_only=True,
        source='condition_set',
        required=False
    )
    attached = serializers.CharField()
    activity = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='Conditions')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = Conditions
        fields = (
            'id',
            'activity',
            'attached',
            'condition',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.conditions(
            activity,
            data.get('attached')
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')

        instance = Conditions.objects.create(**validated_data)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')

        update_instance = Conditions(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance

    def destroy(self, *args, **kwargs):
        activity = Activity.objects.get(pk=kwargs.get('pk'))
        activity.condition.delete()

        activity.modified = True
        activity.save()


class ActivityRecipientRegionSerializer(DynamicFieldsModelSerializer):
    region = BasicRegionSerializer(
        fields=('url', 'code', 'name'),
    )
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=False
    )
    vocabulary = VocabularySerializer()
    vocabulary_uri = serializers.URLField(required=False)

    activity = serializers.CharField(write_only=True)
    narratives = NarrativeSerializer(many=True, required=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ActivityRecipientRegion')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ActivityRecipientRegion
        fields = (
            'id',
            'activity',
            'region',
            'percentage',
            'vocabulary',
            'vocabulary_uri',
            'narratives',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_recipient_region(
            activity,
            data.get('region', {}).get('code'),
            data.get('vocabulary', {}).get('code'),
            data.get('vocabulary_uri'),
            data.get('percentage'),
            getattr(self, 'instance', None),  # only on update
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')

        instance = ActivityRecipientRegion.objects.create(
            **validated_data
        )

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')

        update_instance = ActivityRecipientRegion(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance


class HumanitarianScopeSerializer(DynamicFieldsModelSerializer):
    type = CodelistSerializer()
    vocabulary = VocabularySerializer()
    vocabulary_uri = serializers.URLField()
    code = serializers.CharField()
    activity = serializers.CharField(write_only=True)
    narratives = NarrativeSerializer(many=True, required=False)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='HumanitarianScope')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = HumanitarianScope
        fields = (
            'activity',
            'id',
            'type',
            'vocabulary',
            'vocabulary_uri',
            'code',
            'narratives',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_humanitarian_scope(
            activity,
            data.get('type', {}).get('code'),
            data.get('vocabulary', {}).get('code'),
            data.get('vocabulary_uri'),
            data.get('code'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')

        instance = HumanitarianScope.objects.create(
            **validated_data
        )

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')

        update_instance = HumanitarianScope(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance


class RecipientCountrySerializer(DynamicFieldsModelSerializer):
    country = CountrySerializer(fields=('url', 'code', 'name'))
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=False
    )
    activity = serializers.CharField(write_only=True)
    narratives = NarrativeSerializer(many=True, required=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ActivityRecipientCountry')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_recipient_country(
            activity,
            data.get('country', {}).get('code'),
            data.get('percentage'),
            getattr(self, 'instance', None),  # only on update
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')

        instance = ActivityRecipientCountry.objects.create(
            **validated_data
        )

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')

        update_instance = ActivityRecipientCountry(
            **validated_data
        )
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance

    class Meta:
        model = ActivityRecipientCountry
        fields = (
            'id',
            'activity',
            'country',
            'percentage',
            'narratives',
            'name_space',
        )


class ResultTypeSerializer(ModelSerializerNoValidation):
    class Meta:
        model = ResultType
        fields = (
            'id',
            'code',
            'name',
        )

        extra_kwargs = {"id": {"read_only": False}}


class ResultDescriptionSerializer(ModelSerializerNoValidation):
    narratives = NarrativeSerializer(source="*")

    class Meta:
        model = ResultDescription
        fields = (
            'id',
            'narratives',
        )

        extra_kwargs = {"id": {"read_only": False}}


class ResultTitleSerializer(ModelSerializerNoValidation):
    narratives = NarrativeSerializer(source="*")

    class Meta:
        model = ResultTitle
        fields = (
            'id',
            'narratives',
        )

        extra_kwargs = {"id": {"read_only": False}}


class ResultIndicatorPeriodActualLocationSerializer(ModelSerializerNoValidation):  # NOQA: E501
    ref = serializers.CharField()
    result_indicator_period = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name=obj.__class__.__name__)
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ResultIndicatorPeriodActualLocation
        fields = (
            'id',
            'result_indicator_period',
            'ref',
            'name_space'
        )

    def validate(self, data):

        # See: #747
        raise NotImplementedError("This action is not implemented")

    def create(self, validated_data):

        # See: #747
        raise NotImplementedError("This action is not implemented")

    def update(self, instance, validated_data):

        # See: #747
        raise NotImplementedError("This action is not implemented")


class ResultIndicatorPeriodTargetLocationSerializer(ModelSerializerNoValidation):  # NOQA: E501
    ref = serializers.CharField()
    result_indicator_period_target = serializers.CharField(write_only=True)
    result_indicator_period = serializers.CharField(
        write_only=True,
        source='result_indicator_period_target__result_indicator_period'
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name=obj.__class__.__name__)
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ResultIndicatorPeriodTargetLocation
        fields = (
            'id',
            'result_indicator_period_target',
            'result_indicator_period',
            'ref',
            'name_space',
        )

    def validate(self, data):
        result_indicator_period_target = get_or_raise(
            ResultIndicatorPeriodTarget,
            data,
            'result_indicator_period_target'
        )

        validated = validators.activity_result_indicator_period_location(
            result_indicator_period_target,
            data.get('ref'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        result_indicator_period_target_id = validated_data.get(
            'result_indicator_period_target'
        )
        result_indicator_period = validated_data.get(
            'result_indicator_period'
        )

        instance = ResultIndicatorPeriodTargetLocation.objects.create(
            result_indicator_period_target_id=result_indicator_period_target_id,  # NOQA: E501
            ref=validated_data['ref'],
            location=validated_data['location']
        )

        result_indicator_period.result_indicator.result.activity.modified = True  # NOQA: E501
        result_indicator_period.result_indicator.result.activity.save()

        return instance

    def update(self, instance, validated_data):
        result_indicator_period_target_id = validated_data.get(
            'result_indicator_period_target'
        )
        result_indicator_period = validated_data.get(
            'result_indicator_period'
        )

        update_instance = ResultIndicatorPeriodTargetLocation(
            result_indicator_period_target_id=result_indicator_period_target_id,  # NOQA: E501
            ref=validated_data['ref'],
            location=validated_data['location']
        )
        update_instance.id = instance.id
        update_instance.save()

        result_indicator_period.result_indicator.result.activity.modified = True  # NOQA: E501
        result_indicator_period.result_indicator.result.activity.save()

        return update_instance


class ResultIndicatorPeriodActualDimensionSerializer(ModelSerializerNoValidation):  # NOQA: E501
    name = serializers.CharField()
    value = serializers.CharField()
    result_indicator_period = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name=obj.__class__.__name__)
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ResultIndicatorPeriodActualDimension
        fields = (
            'result_indicator_period',
            'id',
            'name',
            'value',
            'name_space'
        )

    def validate(self, data):
        result_indicator_period = get_or_raise(
            ResultIndicatorPeriod, data, 'result_indicator_period')

        validated = validators.activity_result_indicator_period_dimension(
            result_indicator_period,
            data.get('name'),
            data.get('value'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        result_indicator_period = validated_data.get('result_indicator_period')

        instance = ResultIndicatorPeriodActualDimension.objects.create(
            **validated_data)

        result_indicator_period.result_indicator.result.activity.modified = True  # NOQA: E501
        result_indicator_period.result_indicator.result.activity.save()

        return instance

    def update(self, instance, validated_data):
        result_indicator_period = validated_data.get('result_indicator_period')

        update_instance = ResultIndicatorPeriodActualDimension(
            **validated_data
        )
        update_instance.id = instance.id
        update_instance.save()

        result_indicator_period.result_indicator.result.activity.modified = True  # NOQA: E501
        result_indicator_period.result_indicator.result.activity.save()

        return update_instance


class ResultIndicatorPeriodTargetDimensionSerializer(ModelSerializerNoValidation):  # NOQA: E501
    name = serializers.CharField()
    value = serializers.CharField()
    result_indicator_period = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name=obj.__class__.__name__)
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ResultIndicatorPeriodTargetDimension
        fields = (
            'result_indicator_period',
            'id',
            'name',
            'value',
            'name_space'
        )

    def validate(self, data):
        result_indicator_period = get_or_raise(
            ResultIndicatorPeriod, data, 'result_indicator_period')

        validated = validators.activity_result_indicator_period_dimension(
            result_indicator_period,
            data.get('name'),
            data.get('value'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        result_indicator_period = validated_data.get('result_indicator_period')

        instance = ResultIndicatorPeriodTargetDimension.objects.create(
            **validated_data)

        result_indicator_period.result_indicator.result.activity.modified = True  # NOQA: E501
        result_indicator_period.result_indicator.result.activity.save()

        return instance

    def update(self, instance, validated_data):
        result_indicator_period = validated_data.get('result_indicator_period')

        update_instance = ResultIndicatorPeriodTargetDimension(
            **validated_data
        )
        update_instance.id = instance.id
        update_instance.save()

        result_indicator_period.result_indicator.result.activity.modified = True  # NOQA: E501
        result_indicator_period.result_indicator.result.activity.save()

        return update_instance


class ResultIndicatorPeriodTargetSerializer(SerializerNoValidation):
    value = serializers.DecimalField(
        max_digits=25,
        decimal_places=10
    )
    comment = NarrativeContainerSerializer(
        many=True,
        source="resultindicatorperiodtargetcomment_set",
        read_only=True
    )
    locations = ResultIndicatorPeriodTargetLocationSerializer(
        many=True,
        source="resultindicatorperiodtargetlocation_set",
        read_only=True
    )
    dimensions = ResultIndicatorPeriodTargetDimensionSerializer(
        many=True,
        source="resultindicatorperiodtargetdimension_set",
        read_only=True
    )
    document_links = DocumentLinkSerializer(
        many=True,
        read_only=True,
        source='period_target_document_links'
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name=obj.__class__.__name__)
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data


class ResultIndicatorPeriodActualSerializer(SerializerNoValidation):
    value = serializers.DecimalField(
        max_digits=25,
        decimal_places=10)

    comment = NarrativeContainerSerializer(
        source="resultindicatorperiodactualcomment")
    locations = ResultIndicatorPeriodActualLocationSerializer(
        many=True, source="resultindicatorperiodactuallocation_set",
        read_only=True
    )
    dimensions = ResultIndicatorPeriodActualDimensionSerializer(
        many=True,
        source="resultindicatorperiodactualdimension_set",
        read_only=True
    )
    document_links = DocumentLinkSerializer(
        many=True,
        read_only=True,
        source='period_actual_document_links'
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name=obj.__class__.__name__)
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data


class ResultIndicatorPeriodSerializer(ModelSerializerNoValidation):
    targets = ResultIndicatorPeriodTargetSerializer(many=True)
    actuals = ResultIndicatorPeriodActualSerializer(many=True)

    period_start = serializers.CharField(required=False)
    period_end = serializers.CharField(required=False)

    result_indicator = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name=obj.__class__.__name__)
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ResultIndicatorPeriod
        fields = (
            'result_indicator',
            'id',
            'period_start',
            'period_end',
            'targets',
            'actuals',
            'name_space'
        )

    def validate(self, data):

        # See: #747
        raise NotImplementedError("This action is not implemented")

    def create(self, validated_data):

        # See: #747
        raise NotImplementedError("This action is not implemented")

    def update(self, instance, validated_data):

        # See: #747
        raise NotImplementedError("This action is not implemented")


class ResultIndicatorBaselineDimensionSerializer(ModelSerializerNoValidation):  # NOQA: E501
    name = serializers.CharField()
    value = serializers.CharField()

    class Meta:
        model = ResultIndicatorBaselineDimension
        fields = (

            'id',
            'name',
            'value',
        )


class ResultIndicatorBaselineSerializer(ModelSerializerNoValidation):

    class LocationSerializer(ModelSerializerNoValidation):
        class Meta:
            model = Location
            fields = (
                'ref',
            )

    # year = serializers.CharField(
        # source='baseline_year', required=False, allow_null=True)
    # value = serializers.CharField(
        # source='baseline_value', required=False, allow_null=True)

    # XXX: not sure if this fixes tests:
    year = serializers.CharField(
        required=False, allow_null=True)
    value = serializers.CharField(
        required=False, allow_null=True)
    comment = NarrativeContainerSerializer(
        source='resultindicatorbaselinecomment'
    )

    dimensions = ResultIndicatorBaselineDimensionSerializer(
        many=True,
        source='resultindicatorbaselinedimension_set',
        read_only=True
    )

    document_links = DocumentLinkSerializer(
        many=True,
        read_only=True,
        source='baseline_document_links'
    )

    iso_date = serializers.DateField()

    locations = LocationSerializer(
        many=True,
        read_only=True,
        source='location_set'
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name=obj.__class__.__name__)
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ResultIndicatorBaseline
        fields = (
            'year',
            'value',
            'comment',
            'dimensions',
            'document_links',
            'iso_date',
            'locations',
            'name_space',
        )


class ResultIndicatorReferenceSerializer(ModelSerializerNoValidation):
    vocabulary = VocabularySerializer()
    code = serializers.CharField(required=False)

    result_indicator = serializers.CharField(write_only=True)

    class Meta:
        model = ResultIndicatorReference
        fields = (
            'result_indicator',
            'id',
            'vocabulary',
            'code',
            'indicator_uri',
        )

    def validate(self, data):
        result_indicator = get_or_raise(
            ResultIndicator, data, 'result_indicator')

        validated = validators.activity_result_indicator_reference(
            result_indicator,
            data.get('vocabulary', {}).get('code'),
            data.get('code'),
            data.get('indicator_uri'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        result_indicator = validated_data.get('result_indicator')

        instance = ResultIndicatorReference.objects.create(
            **validated_data)

        result_indicator.result.activity.modified = True
        result_indicator.result.activity.save()

        return instance

    def update(self, instance, validated_data):
        result_indicator = validated_data.get('result_indicator')

        update_instance = ResultIndicatorReference(
            **validated_data)
        update_instance.id = instance.id
        update_instance.save()

        result_indicator.result.activity.modified = True
        result_indicator.result.activity.save()

        return update_instance


class ResultIndicatorSerializer(ModelSerializerNoValidation):
    title = NarrativeContainerSerializer(source="resultindicatortitle")
    description = NarrativeContainerSerializer(
        source="resultindicatordescription")
    #  TODO 2.02 reference = ?
    references = ResultIndicatorReferenceSerializer(
        source='resultindicatorreference_set', many=True, read_only=True)
    baseline = ResultIndicatorBaselineSerializer(
        source='resultindicatorbaseline_set',
        many=True,
        read_only=True
    )
    periods = ResultIndicatorPeriodSerializer(
        source='resultindicatorperiod_set', many=True, read_only=True)
    measure = CodelistSerializer()

    result = serializers.CharField(write_only=True)

    document_links = DocumentLinkSerializer(
        many=True,
        read_only=True,
        source='result_indicator_document_links'
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ResultIndicator')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ResultIndicator
        fields = (
            'result',
            'id',
            'title',
            'description',
            'references',
            'baseline',
            'periods',
            'measure',
            'ascending',
            'aggregation_status',
            'document_links',
            'name_space',
        )

    def validate(self, data):
        result = get_or_raise(Result, data, 'result')

        validated = validators.activity_result_indicator(
            result,
            data.get('measure', {}).get('code'),
            data.get('ascending'),
            data.get('resultindicatortitle', {}).get('narratives'),
            data.get('resultindicatordescription', {}).get('narratives'),
            # data.get('baseline_year'),
            # data.get('baseline_value'),
            data.get('resultindicatorbaselinecomment', {}).get('narratives'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        result = validated_data.get('result')
        title_narratives_data = validated_data.pop('title_narratives', [])
        description_narratives_data = validated_data.pop(
            'description_narratives', [])

        instance = ResultIndicator.objects.create(**validated_data)

        result_indicator_title = ResultIndicatorTitle.objects.create(
            result_indicator=instance)
        result_indicator_description = ResultIndicatorDescription.objects.create(  # NOQA: E501
            result_indicator=instance)

        save_narratives(result_indicator_title,
                        title_narratives_data, result.activity)
        save_narratives(result_indicator_description,
                        description_narratives_data, result.activity)

        result.activity.modified = True
        result.activity.save()

        return instance

    def update(self, instance, validated_data):
        result = validated_data.get('result')
        title_narratives_data = validated_data.pop('title_narratives', [])
        description_narratives_data = validated_data.pop(
            'description_narratives', [])

        update_instance = ResultIndicator(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        save_narratives(instance.resultindicatortitle,
                        title_narratives_data, result.activity)
        save_narratives(
            instance.resultindicatordescription,
            description_narratives_data,
            result.activity)

        result.activity.modified = True
        result.activity.save()

        return update_instance


class ContactInfoSerializer(ModelSerializerNoValidation):
    type = CodelistSerializer()
    organisation = NarrativeContainerSerializer()
    department = NarrativeContainerSerializer()
    person_name = NarrativeContainerSerializer()
    job_title = NarrativeContainerSerializer()
    mailing_address = NarrativeContainerSerializer()

    activity = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ContactInfo')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_contact_info(
            activity,
            data.get('type', {}).get('code'),
            data.get('organisation'),
            data.get('department'),
            data.get('person_name'),
            data.get('job_title'),
            data.get('telephone'),  # text
            data.get('email'),  # text
            data.get('website'),  # text
            data.get('mailing_address'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')

        organisation_data = validated_data.pop('organisation', None)
        organisation_narratives_data = validated_data.pop(
            'organisation_narratives', None)
        department_data = validated_data.pop('department', None)
        department_narratives_data = validated_data.pop(
            'department_narratives', None)
        person_name_data = validated_data.pop('person_name', None)
        person_name_narratives_data = validated_data.pop(
            'person_name_narratives', None)
        job_title_data = validated_data.pop('job_title', None)
        job_title_narratives_data = validated_data.pop(
            'job_title_narratives', None)
        mailing_address_data = validated_data.pop('mailing_address', None)
        mailing_address_narratives_data = validated_data.pop(
            'mailing_address_narratives', None)

        instance = ContactInfo.objects.create(**validated_data)

        if organisation_data is not None:
            organisation = ContactInfoOrganisation.objects.create(
                contact_info=instance,
                **organisation_data)
            instance.organisation = organisation

            if organisation_narratives_data:
                save_narratives(
                    organisation, organisation_narratives_data, activity)

        if department_data is not None:
            department = ContactInfoDepartment.objects.create(
                contact_info=instance,
                **department_data)
            instance.department = department

            if department_narratives_data:
                save_narratives(
                    department, department_narratives_data, activity)

        if person_name_data is not None:
            person_name = ContactInfoPersonName.objects.create(
                contact_info=instance,
                **person_name_data)
            instance.person_name = person_name

            if person_name_narratives_data:
                save_narratives(
                    person_name, person_name_narratives_data, activity)

        if job_title_data is not None:
            job_title = ContactInfoJobTitle.objects.create(
                contact_info=instance,
                **job_title_data)
            instance.job_title = job_title

            if job_title_narratives_data:
                save_narratives(job_title, job_title_narratives_data, activity)

        if mailing_address_data is not None:
            mailing_address = ContactInfoMailingAddress.objects.create(
                contact_info=instance,
                **mailing_address_data)
            instance.mailing_address = mailing_address

            if mailing_address_narratives_data:
                save_narratives(mailing_address,
                                mailing_address_narratives_data, activity)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')
        organisation_data = validated_data.pop('organisation', None)
        organisation_narratives_data = validated_data.pop(
            'organisation_narratives', None)
        department_data = validated_data.pop('department', None)
        department_narratives_data = validated_data.pop(
            'department_narratives', None)
        person_name_data = validated_data.pop('person_name', None)
        person_name_narratives_data = validated_data.pop(
            'person_name_narratives', None)
        job_title_data = validated_data.pop('job_title', None)
        job_title_narratives_data = validated_data.pop(
            'job_title_narratives', None)
        mailing_address_data = validated_data.pop('mailing_address', None)
        mailing_address_narratives_data = validated_data.pop(
            'mailing_address_narratives', None)

        update_instance = ContactInfo(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        if organisation_data is not None:
            organisation, created = ContactInfoOrganisation.objects.update_or_create(  # NOQA: E501
                contact_info=instance,
                defaults=organisation_data)
            update_instance.organisation = organisation

            if organisation_narratives_data:
                save_narratives(
                    organisation, organisation_narratives_data, activity)

        if department_data is not None:
            department, created = ContactInfoDepartment.objects.update_or_create(  # NOQA: E501
                contact_info=instance,
                defaults=department_data)
            update_instance.department = department

            if department_narratives_data:
                save_narratives(
                    department, department_narratives_data, activity)

        if person_name_data is not None:
            person_name, created = ContactInfoPersonName.objects.update_or_create(  # NOQA: E501
                contact_info=instance,
                defaults=person_name_data)
            update_instance.person_name = person_name

            if person_name_narratives_data:
                save_narratives(
                    person_name, person_name_narratives_data, activity)

        if job_title_data is not None:
            job_title, created = ContactInfoJobTitle.objects.update_or_create(
                contact_info=instance,
                defaults=job_title_data)
            update_instance.job_title = job_title

            if job_title_narratives_data:
                save_narratives(job_title, job_title_narratives_data, activity)

        if mailing_address_data is not None:
            mailing_address, created = ContactInfoMailingAddress.objects.update_or_create(  # NOQA: E501
                contact_info=instance, defaults=mailing_address_data)
            update_instance.mailing_address = mailing_address

            if mailing_address_narratives_data:
                save_narratives(mailing_address,
                                mailing_address_narratives_data, activity)

        activity.modified = True
        activity.save()

        return update_instance

    class Meta:
        model = ContactInfo
        fields = (
            'id',
            'activity',
            'type',
            'organisation',
            'department',
            'person_name',
            'job_title',
            'telephone',
            'email',
            'website',
            'mailing_address',
            'name_space',
        )


class ResultReferenceSerializer(ModelSerializerNoValidation):
    vocabulary = VocabularySerializer()
    code = serializers.CharField(required=False)

    result = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ResultReference')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ResultReference
        fields = (
            'result',
            'id',
            'vocabulary',
            'code',
            'vocabulary_uri',
            'name_space',
        )

    def validate(self, data):
        result = get_or_raise(
            Result, data, 'result')

        validated = validators.activity_result_reference(
            result,
            data.get('vocabulary', {}).get('code'),
            data.get('code'),
            data.get('vocabulary_uri'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        result = validated_data.get('result')

        instance = ResultReference.objects.create(
            **validated_data)

        result.activity.modified = True
        result.activity.save()

        return instance

    def update(self, instance, validated_data):
        result = validated_data.get('result')

        update_instance = ResultReference(
            **validated_data)
        update_instance.id = instance.id
        update_instance.save()

        result.activity.modified = True
        result.activity.save()

        return update_instance


class ResultSerializer(ModelSerializerNoValidation):
    type = CodelistSerializer()
    title = NarrativeContainerSerializer(source="resulttitle")
    description = NarrativeContainerSerializer(source="resultdescription")
    indicators = ResultIndicatorSerializer(
        source='resultindicator_set', many=True, read_only=True)
    reference = ResultReferenceSerializer(
        source='resultreference_set', many=True, read_only=True)

    activity = serializers.CharField(write_only=True)

    document_links = DocumentLinkSerializer(
        many=True,
        read_only=True,
        source='documentlink_set'
    )

    sectors = ActivitySectorSerializer(
        many=True,
        source='activity.activitysector_set',
        read_only=True,
        required=False,
    )

    recipient_countries = RecipientCountrySerializer(
        many=True,
        source='activity.activityrecipientcountry_set',
        read_only=True,
        required=False,
    )
    recipient_regions = ActivityRecipientRegionSerializer(
        many=True,
        source='activity.activityrecipientregion_set',
        read_only=True,
        required=False,
    )

    iati_identifier = serializers.CharField(source='activity.iati_identifier', required=False)  # NOQA: E501

    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='Result')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = Result
        fields = (
            'id',
            'activity',
            'title',
            'description',
            'indicators',
            'type',
            'aggregation_status',
            'document_links',
            'sectors',
            'recipient_countries',
            'recipient_regions',
            'iati_identifier',
            'reference',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_result(
            activity,
            data.get('type', {}).get('code'),
            data.get('aggregation_status'),
            data.get('resulttitle', {}).get('narratives'),
            data.get('resultdescription', {}).get('narratives'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')
        title_narratives_data = validated_data.pop('title_narratives', [])
        description_narratives_data = validated_data.pop(
            'description_narratives', [])

        instance = Result.objects.create(**validated_data)

        result_title = ResultTitle.objects.create(result=instance)
        result_description = ResultDescription.objects.create(
            result=instance)

        save_narratives(result_title, title_narratives_data, activity)
        save_narratives(result_description,
                        description_narratives_data, activity)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')
        title_narratives_data = validated_data.pop('title_narratives', [])
        description_narratives_data = validated_data.pop(
            'description_narratives', [])

        update_instance = Result(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        save_narratives(update_instance.resulttitle,
                        title_narratives_data, activity)
        save_narratives(update_instance.resultdescription,
                        description_narratives_data, activity)

        activity.modified = True
        activity.save()

        return update_instance


class CrsAddLoanTermsSerializer(ModelSerializerNoValidation):
    repayment_type = CodelistSerializer()
    repayment_plan = CodelistSerializer()
    commitment_date = serializers.CharField()
    repayment_first_date = serializers.CharField()
    repayment_final_date = serializers.CharField()
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='CrsAddLoanTerms')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = CrsAddLoanTerms
        fields = (
            'rate_1',
            'rate_2',
            'repayment_type',
            'repayment_plan',
            'commitment_date',
            'repayment_first_date',
            'repayment_final_date',
            'name_space',
        )


class CrsAddLoanStatusSerializer(ModelSerializerNoValidation):
    value_date = serializers.CharField()
    currency = CodelistSerializer()
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='CrsAddLoanStatus')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = CrsAddLoanStatus
        fields = (
            'year',
            'currency',
            'value_date',
            'interest_received',
            'principal_outstanding',
            'principal_arrears',
            'interest_arrears',
            'name_space',
        )


class CrsAddOtherFlagsSerializer(ModelSerializerNoValidation):
    other_flags = CodelistSerializer()
    significance = serializers.CharField()

    crs_add = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='CrsAddOtherFlags')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = CrsAddOtherFlags
        fields = (
            'crs_add',
            'id',
            'other_flags',
            'significance',
            'name_space',
        )

    def validate(self, data):
        crs_add = get_or_raise(CrsAdd, data, 'crs_add')

        validated = validators.crs_add_other_flags(
            crs_add,
            data.get('other_flags', {}).get('code'),
            data.get('significance'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        crs_add = validated_data.get('crs_add')

        instance = CrsAddOtherFlags.objects.create(
            **validated_data)

        crs_add.activity.modified = True
        crs_add.activity.save()

        return instance

    def update(self, instance, validated_data):
        crs_add = validated_data.get('crs_add')

        update_instance = CrsAddOtherFlags(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        crs_add.activity.modified = True
        crs_add.activity.save()

        return update_instance


class CrsAddSerializer(ModelSerializerNoValidation):
    other_flags = CrsAddOtherFlagsSerializer(many=True, required=False)
    loan_terms = CrsAddLoanTermsSerializer(required=False)
    loan_status = CrsAddLoanStatusSerializer(required=False)
    channel_code = CodelistSerializer()
    activity = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='CrsAdd')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = CrsAdd
        fields = (
            'activity',
            'id',
            'channel_code',
            'other_flags',
            'loan_terms',
            'loan_status',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        crs_add = validators.crs_add(
            activity,
            data.get('channel_code')
        )

        loan_terms = validators.crs_add_loan_terms(
            activity,
            data.get('loan_terms', {}).get('rate_1'),
            data.get('loan_terms', {}).get('rate_2'),
            data.get('loan_terms', {}).get('repayment_type', {}).get('code'),
            data.get('loan_terms', {}).get('repayment_plan', {}).get('code'),
            data.get('loan_terms', {}).get('commitment_date'),
            data.get('loan_terms', {}).get('repayment_first_date'),
            data.get('loan_terms', {}).get('repayment_final_date'),
        )

        loan_status = validators.crs_add_loan_status(
            activity,
            data.get('loan_status', {}).get('year'),
            data.get('loan_status', {}).get('currency').get('code'),
            data.get('loan_status', {}).get('value_date'),
            data.get('loan_status', {}).get('interest_received'),
            data.get('loan_status', {}).get('principal_outstanding'),
            data.get('loan_status', {}).get('principal_arrears'),
            data.get('loan_status', {}).get('interest_arrears'),
        )

        return handle_errors(crs_add, loan_terms, loan_status)

    def create(self, validated_data):
        activity = validated_data.get('activity')
        loan_terms = validated_data.pop('loan_terms', {})
        loan_status = validated_data.pop('loan_status', {})

        instance = CrsAdd.objects.create(**validated_data)

        loan_terms = CrsAddLoanTerms.objects.create(
            crs_add=instance,
            **loan_terms)

        loan_status = CrsAddLoanStatus.objects.create(
            crs_add=instance,
            **loan_status)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')
        loan_terms = validated_data.pop('loan_terms')
        loan_status = validated_data.pop('loan_status')

        update_instance = CrsAdd(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        updated_loan_terms = CrsAddLoanTerms(**loan_terms)
        updated_loan_terms.crs_add = update_instance
        updated_loan_terms.id = instance.loan_terms.id
        updated_loan_terms.save()

        updated_loan_status = CrsAddLoanStatus(**loan_status)
        updated_loan_status.crs_add = update_instance
        updated_loan_status.id = instance.loan_status.id
        updated_loan_status.save()

        activity.modified = True
        activity.save()

        return update_instance


class FssForecastSerializer(ModelSerializerNoValidation):
    value_date = serializers.CharField()
    currency = CodelistSerializer()

    fss = serializers.CharField(write_only=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='FssForecast')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = FssForecast
        fields = (
            'id',
            'fss',
            'year',
            'value_date',
            'currency',
            'value',
            'name_space',
        )

    def validate(self, data):
        fss = get_or_raise(Fss, data, 'fss')

        validated = validators.fss_forecast(
            fss,
            data.get('year'),
            data.get('value_date'),
            data.get('currency', {}).get('code'),
            data.get('value'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        fss = validated_data.get('fss')

        instance = FssForecast.objects.create(**validated_data)

        fss.activity.modified = True
        fss.activity.save()

        return instance

    def update(self, instance, validated_data):
        fss = validated_data.get('fss')

        update_instance = FssForecast(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        fss.activity.modified = True
        fss.activity.save()

        return update_instance


class FssSerializer(ModelSerializerNoValidation):
    extraction_date = serializers.CharField()
    forecasts = FssForecastSerializer(
        many=True,
        source='fssforecast_set',
        required=False
    )

    activity = serializers.CharField(write_only=True)

    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='Fss')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = Fss
        fields = (
            'id',
            'activity',
            'extraction_date',
            'priority',
            'phaseout_year',
            'forecasts',
            'name_space',
        )

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.fss(
            activity,
            data.get('extraction_date'),
            data.get('priority'),
            data.get('phaseout_year'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')
        instance = Fss.objects.create(**validated_data)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')

        update_instance = Fss(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        activity.modified = True
        activity.save()

        return update_instance


class LocationSerializer(DynamicFieldsModelSerializer):
    class LocationIdSerializer(SerializerNoValidation):
        vocabulary = VocabularySerializer(
            source='location_id_vocabulary')
        code = serializers.CharField(source='location_id_code')

    class PointSerializer(SerializerNoValidation):
        pos = PointField(source='point_pos')
        srsName = serializers.CharField(source="point_srs_name")

    class AdministrativeSerializer(ModelSerializerNoValidation):
        code = serializers.CharField()
        vocabulary = VocabularySerializer()

        class Meta:
            model = LocationAdministrative
            fields = (
                'id',
                'code',
                'vocabulary',
                'level',
            )

    location_reach = CodelistSerializer()
    location_id = LocationIdSerializer(source='*')
    name = NarrativeContainerSerializer()
    description = NarrativeContainerSerializer()
    activity_description = NarrativeContainerSerializer()

    # administrative has its own view
    administrative = AdministrativeSerializer(
        many=True,
        source="locationadministrative_set",
        read_only=True
    )

    point = PointSerializer(source="*")
    exactness = CodelistSerializer()
    location_class = CodelistSerializer()
    feature_designation = CodelistSerializer()

    activity = serializers.CharField(write_only=True)

    # TODO: slow fields so ignored them, until we have a good solution
    """
    sectors = ActivitySectorSerializer(
        many=True,
        source='activity.activitysector_set',
        read_only=True,
        required=False,
    )

    recipient_countries = RecipientCountrySerializer(
        many=True,
        source='activity.activityrecipientcountry_set',
        read_only=True,
        required=False,
    )
    recipient_regions = ActivityRecipientRegionSerializer(
        many=True,
        source='activity.activityrecipientregion_set',
        read_only=True,
        required=False,
    )
    """

    reporting_organisations = ReportingOrganisationDataSerializer(
        many=True,
        source='activity.reporting_organisations',
        required=False,
        read_only=True,

    )
    iati_identifier = serializers.CharField(source='activity.iati_identifier', required=False)  # NOQA: E501
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='Location')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    def validate(self, data):
        activity = get_or_raise(Activity, data, 'activity')

        validated = validators.activity_location(
            activity,
            data.get('ref'),
            data.get('location_reach', {}).get('code'),
            data.get('location_id_code', {}),
            data.get('location_id_vocabulary', {}).get('code'),
            data.get('name', {}).get('narratives'),
            data.get('description', {}).get('narratives'),
            data.get('activity_description', {}).get('narratives'),
            data.get('point_srs_name', {}),
            data.get('point_pos', {}),
            data.get('exactness', {}).get('code'),
            data.get('location_class', {}).get('code'),
            data.get('feature_designation', {}).get('code'),
        )

        return handle_errors(validated)

    def create(self, validated_data):
        activity = validated_data.get('activity')
        name_narratives = validated_data.pop('name_narratives', [])
        description_narratives = validated_data.pop(
            'description_narratives', [])
        activity_description_narratives = validated_data.pop(
            'activity_description_narratives', [])

        instance = Location.objects.create(**validated_data)

        location_name = LocationName.objects.create(
            location=instance)
        location_description = LocationDescription.objects.create(
            location=instance)
        location_activity_description = LocationActivityDescription.objects.create(  # NOQA: E501
            location=instance)

        save_narratives(location_name, name_narratives, activity)
        save_narratives(location_description, description_narratives, activity)
        save_narratives(location_activity_description,
                        activity_description_narratives, activity)

        activity.modified = True
        activity.save()

        return instance

    def update(self, instance, validated_data):
        activity = validated_data.get('activity')
        name_narratives = validated_data.pop('name_narratives', [])
        description_narratives = validated_data.pop(
            'description_narratives', [])
        activity_description_narratives = validated_data.pop(
            'activity_description_narratives', [])

        update_instance = Location(**validated_data)
        update_instance.id = instance.id
        update_instance.save()

        location_name = LocationName.objects.get(location=instance)
        location_description = LocationDescription.objects.get(
            location=instance)
        location_activity_description = LocationActivityDescription.objects.get(  # NOQA: E501
            location=instance)

        save_narratives(location_name, name_narratives, activity)
        save_narratives(location_description, description_narratives, activity)
        save_narratives(location_activity_description,
                        activity_description_narratives, activity)

        activity.modified = True
        activity.save()

        return update_instance

    class Meta:
        model = Location
        fields = (
            'id',
            'activity',
            'iati_identifier',
            'ref',
            'location_reach',
            'location_id',
            'name',
            'description',
            'activity_description',
            'administrative',
            'point',
            'exactness',
            'location_class',
            'feature_designation',
            # TODO: slow fields so ignored them, until we have a good solution
            # 'sectors',
            # 'recipient_countries',
            # 'recipient_regions'
            'reporting_organisations',
            'name_space',
        )


class PublishedStateSerializer(DynamicFieldsSerializer):
    published = serializers.BooleanField()
    ready_to_publish = serializers.BooleanField()
    modified = serializers.BooleanField()


class ActivityAggregationContainerSerializer(DynamicFieldsSerializer):
    activity = ActivityAggregationSerializer(source='activity_aggregation')
    children = ActivityAggregationSerializer(source='child_aggregation')
    activity_children = ActivityAggregationSerializer(
        source='activity_plus_child_aggregation')


class TransactionProviderSerializer(serializers.ModelSerializer):
    ref = serializers.CharField()
    type = CodelistSerializer()
    narratives = NarrativeSerializer(many=True)
    provider_activity = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='activities:activity-detail')
    provider_activity_id = serializers.CharField(
        source="provider_activity_ref", required=False)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='TransactionProvider')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = TransactionProvider
        fields = (
            'ref',
            'type',
            'provider_activity',
            'provider_activity_id',
            'narratives',
            'name_space',
        )


class TransactionReceiverSerializer(serializers.ModelSerializer):
    ref = serializers.CharField()
    type = CodelistSerializer()
    narratives = NarrativeSerializer(many=True)
    receiver_activity = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='activities:activity-detail')
    receiver_activity_id = serializers.CharField(
        source="receiver_activity_ref"
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='TransactionReceiver')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = TransactionReceiver
        fields = (
            'ref',
            'type',
            'receiver_activity',
            'receiver_activity_id',
            'narratives',
            'name_space',
        )


class TransactionRecipientCountrySerializer(serializers.ModelSerializer):
    country = CountrySerializer(fields=('code', ))
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='TransactionRecipientCountry')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = TransactionRecipientCountry
        fields = (
            'country',
            'percentage',
            'name_space',
        )


class TransactionRecipientRegionSerializer(serializers.ModelSerializer):
    region = BasicRegionSerializer(
        fields=('code', ),
    )
    vocabulary = VocabularySerializer()
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='TransactionRecipientRegion')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = TransactionRecipientRegion
        fields = (
            'region',
            'vocabulary',
            'name_space',
        )


class TransactionSectorSerializer(serializers.ModelSerializer):
    sector = SectorSerializer(fields=('code', ))
    vocabulary = VocabularySerializer()
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='TransactionSector')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = TransactionSector
        fields = (
            'sector',
            'vocabulary',
            'name_space',
        )


class TransactionDescriptionSerializer(serializers.ModelSerializer):
    narratives = NarrativeSerializer(many=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='TransactionDescription')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = TransactionDescription
        fields = (
            'narratives',
            'name_space',
        )


class TransactionAidTypeSerializer(serializers.ModelSerializer):
    aid_type = AidTypeSerializer()
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='TransactionAidtype')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = TransactionAidType
        fields = (
            'aid_type',
            'name_space',
        )


class TransactionSerializer(serializers.ModelSerializer):
    """
    Transaction serializer class
    """
    transaction_date = serializers.CharField()
    value_date = serializers.CharField()
    # Aid type for version 2.03
    aid_types = TransactionAidTypeSerializer(
        many=True,
        source='transactionaidtype_set',
        read_only=True
    )
    # Aid type for version 2.02 or below
    aid_type = CodelistSerializer()
    disbursement_channel = CodelistSerializer()
    finance_type = CodelistSerializer()
    flow_type = CodelistSerializer()
    tied_status = CodelistSerializer()
    transaction_type = CodelistSerializer()
    currency = CodelistSerializer()
    humanitarian = serializers.BooleanField()
    provider_organisation = TransactionProviderSerializer(required=False)
    receiver_organisation = TransactionReceiverSerializer(required=False)
    recipient_countries = TransactionRecipientCountrySerializer(
        many=True,
        source='transactionrecipientcountry_set',
        read_only=True
    )
    recipient_regions = TransactionRecipientRegionSerializer(
        many=True,
        source='transactionrecipientregion_set',
        read_only=True
    )
    sectors = TransactionSectorSerializer(
        many=True,
        source='transactionsector_set',
        read_only=True
    )
    description = TransactionDescriptionSerializer(
        read_only=True
    )
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='Transaction')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = Transaction
        fields = (
            'ref',
            'humanitarian',
            'transaction_type',
            'transaction_date',
            'value',
            'value_date',
            'currency',
            'description',
            'provider_organisation',
            'receiver_organisation',
            'disbursement_channel',
            'sectors',
            'recipient_countries',
            'recipient_regions',
            'flow_type',
            'finance_type',
            'aid_types',
            'aid_type',
            'tied_status',
            'name_space',
        )


class ActivityTagSerializer(ModelSerializerNoValidation):
    vocabulary = VocabularySerializer()
    narratives = NarrativeSerializer(many=True)
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ActivityTag')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ActivityTag
        fields = (
            'id',
            'code',
            'vocabulary_uri',
            'activity',
            'vocabulary',
            'narratives'
        )


class ActivityDefaultAidTypeSerializer(ModelSerializerNoValidation):
    aid_type = AidTypeSerializer()
    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='ActivityDefaultAidType')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    class Meta:
        model = ActivityDefaultAidType
        fields = (
            'aid_type',
            'name_space',
        )


class NameSpaceSerializer(ModelSerializerNoValidation):

    class Meta:
        model = NameSpaceElement
        fields = (
            'namespace',
            'nsmap',
            'sub_element',
        )


class ActivitySerializer(DynamicFieldsModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='activities:activity-detail', read_only=True)

    id = serializers.CharField(required=False)
    iati_identifier = serializers.CharField()

    name_space = serializers.SerializerMethodField(required=False)

    def get_name_space(self, obj):
        try:
            name_space = NameSpaceElement.objects.filter(
                parent_element_id=obj.pk).filter(
                parent_element_name='Activity')
            namespace_serializer = NameSpaceSerializer(name_space, many=True)
        except NameSpaceElement.DoesNotExist:
            return None
            pass
        return namespace_serializer.data

    reporting_org = ReportingOrganisationDataSerializer(
        read_only=True,
        source="reporting_organisations.first"
    )

    title = TitleSerializer(required=False)

    descriptions = DescriptionSerializer(
        many=True,
        source='description_set',
        read_only=True,
    )
    participating_organisations = ParticipatingOrganisationSerializer(
        many=True,
        read_only=True,
    )

    # TODO ; add other-identifier serializer
    other_identifier = OtherIdentifierSerializer(
        many=True, source="otheridentifier_set", required=False)

    activity_status = CodelistSerializer(required=False)
    budget_not_provided = CodelistSerializer(required=False)
    activity_dates = ActivityDateSerializer(
        many=True,
        source='activitydate_set',
        read_only=True,
    )

    # TODO ; add contact-info serializer
    # note; contact info has a sequence we should use in the
    # ContactInfoSerializer!
    contact_info = ContactInfoSerializer(
        many=True,
        source="contactinfo_set",
        read_only=True,
        required=False,
    )

    activity_scope = CodelistSerializer(source='scope', required=False)
    recipient_countries = RecipientCountrySerializer(
        many=True,
        source='activityrecipientcountry_set',
        read_only=True,
        required=False,
    )
    recipient_regions = ActivityRecipientRegionSerializer(
        many=True,
        source='activityrecipientregion_set',
        read_only=True,
        required=False,
    )
    locations = LocationSerializer(
        many=True,
        source='location_set',
        read_only=True,
        required=False,
    )
    sectors = ActivitySectorSerializer(
        many=True,
        source='activitysector_set',
        read_only=True,
        required=False,
    )

    tags = ActivityTagSerializer(
        many=True,
        source='activitytag_set',
        read_only=True,
        required=False,
    )

    # TODO ; add country-budget-items serializer
    country_budget_items = CountryBudgetItemsSerializer(required=False)

    humanitarian_scope = HumanitarianScopeSerializer(
        many=True,
        source='humanitarianscope_set',
        read_only=True,
        required=False,
    )

    policy_markers = ActivityPolicyMarkerSerializer(
        many=True,
        source='activitypolicymarker_set',
        read_only=True,
        required=False,
    )

    collaboration_type = CodelistSerializer(required=False)
    default_flow_type = CodelistSerializer(required=False)
    default_finance_type = CodelistSerializer(required=False)
    default_aid_type = ActivityDefaultAidTypeSerializer(
        many=True,
        source='default_aid_types',
        read_only=True,
        required=False,
    )
    default_tied_status = CodelistSerializer(required=False)

    budgets = BudgetSerializer(
        many=True,
        source='budget_set',
        read_only=True,
    )

    # note; planned-disbursement has a sequence in
    # PlannedDisbursementSerializer
    planned_disbursements = PlannedDisbursementSerializer(
        many=True,
        source='planneddisbursement_set',
        read_only=True,
    )

    # capital_spend = CapitalSpendSerializer(required=False)
    capital_spend = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=False,
        required=False,
    )

    transactions = serializers.HyperlinkedIdentityField(
        read_only=True,
        view_name='activities:activity-transactions',
    )
    transaction_url = serializers.HyperlinkedIdentityField(
        read_only=True,
        view_name='activities:activity-transactions-by-iati-identifier',
        lookup_field='iati_identifier'
    )

    related_transactions = TransactionSerializer(
        many=True,
        source='transaction_set',
        read_only=True
    )

    document_links = DocumentLinkSerializer(
        many=True,
        read_only=True,
        source='documentlink_set')
    related_activities = RelatedActivitySerializer(
        many=True,
        read_only=True,
        source='relatedactivity_set')

    legacy_data = LegacyDataSerializer(
        many=True, source="legacydata_set", required=False)

    conditions = ConditionsSerializer(required=False)

    results = ResultSerializer(
        many=True,
        read_only=True,
        source="result_set")

    # note; crs-add has a sequence in CrsAddSerializer
    crs_add = CrsAddSerializer(many=True, source="crsadd_set", required=False)

    fss = FssSerializer(many=True, source="fss_set", required=False)

    # activity attributes
    last_updated_datetime = serializers.DateTimeField(required=False)
    xml_lang = serializers.CharField(
        source='default_lang.code', required=False)
    default_currency = CodelistSerializer(required=False)

    humanitarian = serializers.BooleanField(required=False)

    # from reporting-org, can be saved directly on activity
    secondary_reporter = serializers.BooleanField(
        write_only=True, required=False)

    # other added data
    activity_plus_child_aggregation = ActivityAggregationContainerSerializer(
        source="*", read_only=True)

    dataset = SimpleDatasetSerializer(
        read_only=True,
        fields=(
            'id',
            'iati_id',
            'name',
            'title',
            'source_url'))

    publisher = PublisherSerializer(
        read_only=True,
        fields=(
            'id',
            'url',
            'publisher_iati_id',
            'display_name',
            'name'))

    published_state = PublishedStateSerializer(source="*", read_only=True)

    transaction_types = serializers.SerializerMethodField()

    @classmethod
    def get_transaction_types(cls, obj):
        return list(Transaction.objects.filter(activity=obj).values('transaction_type').annotate(dsum=Sum('value')))  # NOQA: E501
        # return Transaction.objects.filter(activity=obj).aggregate(Sum('value'))  # NOQA: E501

    def validate(self, data):
        validated = validators.activity(
            data.get('iati_identifier'),
            data.get('default_lang', {}).get('code'),
            data.get('hierarchy'),
            data.get('humanitarian'),
            data.get('last_updated_datetime'),
            data.get('linked_data_uri'),
            data.get('default_currency'),
            data.get('dataset'),
            data.get('activity_status', {}).get('code'),
            data.get('scope', {}).get('code'),
            data.get('collaboration_type', {}).get('code'),
            data.get('default_flow_type', {}).get('code'),
            data.get('default_finance_type', {}).get('code'),
            data.get('default_aid_type', {}).get('code'),
            data.get('default_tied_status', {}).get('code'),
            data.get('planned_start'),
            data.get('actual_start'),
            data.get('start_date'),
            data.get('planned_end'),
            data.get('actual_end'),
            data.get('end_date'),
            data.get('capital_spend'),
            data.get('secondary_reporter'),
            data.get('title', {}),
        )

        return handle_errors(validated)

    def create(self, validated_data):

        old_activity = get_or_none(
            Activity, validated_data, 'iati_identifier')

        if old_activity:
            raise ValidationError({
                "iati_identifier": "Activity with this IATI identifier already exists"  # NOQA: E501
            })

        title_data = validated_data.pop('title', None)  # NOQA: F841
        title_narratives_data = validated_data.pop('title_narratives', None)
        activity_status = validated_data.pop('activity_status', None)
        activity_scope = validated_data.pop('activity_scope', None)
        collaboration_type = validated_data.pop('collaboration_type', None)
        default_flow_type = validated_data.pop('default_flow_type', None)
        default_finance_type = validated_data.pop('default_finance_type', None)
        default_aid_type = validated_data.pop('default_aid_type', None)
        default_tied_status = validated_data.pop('default_tied_status', None)

        instance = Activity(**validated_data)

        instance.activity_status = activity_status
        instance.scope = activity_scope
        instance.collaboration_type = collaboration_type
        instance.default_flow_type = default_flow_type
        instance.default_finance_type = default_finance_type
        instance.default_aid_type = default_aid_type
        instance.default_tied_status = default_tied_status

        # this is set on the view
        instance.publisher_id = self.context['view'].kwargs.get('publisher_id')
        instance.published = False
        instance.ready_to_publish = False
        instance.modified = True

        instance.save()

        title = Title.objects.create(activity=instance)
        instance.title = title

        if title_narratives_data:
            save_narratives(title, title_narratives_data, instance)

        return instance

    def update(self, instance, validated_data):
        title_data = validated_data.pop('title', None)  # NOQA: F841
        title_narratives_data = validated_data.pop('title_narratives', None)
        activity_status = validated_data.pop('activity_status', None)
        activity_scope = validated_data.pop('activity_scope', None)
        collaboration_type = validated_data.pop('collaboration_type', None)
        default_flow_type = validated_data.pop('default_flow_type', None)
        default_finance_type = validated_data.pop('default_finance_type', None)
        default_aid_type = validated_data.pop('default_aid_type', None)
        default_tied_status = validated_data.pop('default_tied_status', None)

        # update_instance = Activity(**validated_data)
        update_instance = instance
        for (key, value) in validated_data.items():
            setattr(update_instance, key, value)
        # update_instance.id = instance.id

        update_instance.activity_status = activity_status
        update_instance.scope = activity_scope
        update_instance.collaboration_type = collaboration_type
        update_instance.default_flow_type = default_flow_type
        update_instance.default_finance_type = default_finance_type
        update_instance.default_aid_type = default_aid_type
        update_instance.default_tied_status = default_tied_status

        update_instance.modified = True

        update_instance.save()

        if title_narratives_data:
            save_narratives(update_instance.title,
                            title_narratives_data, instance)

        return update_instance

    def to_representation(self, instance):
        """
        Custom render to avoid auto render of related transaction
        """
        ret = OrderedDict()
        fields = self._readable_fields

        for field in fields:
            try:
                attribute = field.get_attribute(instance)
            except SkipField:
                continue

            # We skip `to_representation` for `None` values so that fields do
            # not have to explicitly deal with that case.
            #
            # For related fields with `use_pk_only_optimization` we need to
            # resolve the pk value.
            check_for_none = attribute.pk if isinstance(
                attribute, PKOnlyObject
            ) else attribute

            if check_for_none is None:
                ret[field.field_name] = None
            else:
                # Some activity has many related transaction,
                # the request will take too long.
                # So related transaction will be shown if it is on fields
                # request
                if field.field_name in ['related_transactions',
                                        'budgets',
                                        'results',
                                        ]:

                    if field.field_name not in ret:
                        if field.field_name == 'related_transactions' and \
                                instance.transaction_set.count() > 100:
                            custom_ret1 = OrderedDict()
                            custom_ret1['message'] = \
                                'This activity has more ' \
                                'than 100 transactions! ' \
                                'To get all transactions,  ' \
                                'please use the transaction endpoint ' \
                                'instead!'

                            ret[field.field_name] = custom_ret1

                        elif field.field_name == 'results' and \
                                instance.result_set.count() > 100:
                            custom_ret2 = OrderedDict()
                            custom_ret2['message'] = \
                                'This activity has more ' \
                                'than 100 results! ' \
                                'To get all results,  ' \
                                'please use the results ' \
                                'endpoint instead!'

                            ret[field.field_name] = custom_ret2

                        elif field.field_name == 'budgets' \
                                and \
                                instance.budget_set.count() > \
                                100:
                            custom_ret3 = OrderedDict()
                            custom_ret3['message'] = \
                                'This activity has more ' \
                                'than 100 budgets! ' \
                                'To get all budgets,  ' \
                                'please use the budget ' \
                                'endpoint instead!'

                            ret[field.field_name] = custom_ret3

                        else:
                            ret[field.field_name] = field.to_representation(
                                attribute
                            )

                else:
                    ret[field.field_name] = field.to_representation(attribute)

        return ret

    class Meta:
        model = Activity
        fields = (
            'url',
            'id',
            'iati_identifier',
            'reporting_org',
            'title',
            'descriptions',
            'participating_organisations',
            'other_identifier',
            'activity_status',
            'budget_not_provided',
            'activity_dates',
            'contact_info',
            'activity_scope',
            'recipient_countries',
            'recipient_regions',
            'locations',
            'sectors',
            'tags',
            'country_budget_items',
            'humanitarian',
            'humanitarian_scope',
            'policy_markers',
            'collaboration_type',
            'default_flow_type',
            'default_finance_type',
            'default_aid_type',
            'default_tied_status',
            'budgets',
            'planned_disbursements',
            'capital_spend',
            'transactions',
            'related_transactions',
            'document_links',
            'related_activities',
            'legacy_data',
            'conditions',
            'results',
            'crs_add',
            'fss',
            'last_updated_datetime',
            'xml_lang',
            'default_currency',
            'humanitarian',
            'hierarchy',
            'linked_data_uri',
            'secondary_reporter',
            'activity_plus_child_aggregation',
            'dataset',
            'publisher',
            'published_state',
            'transaction_types',
            'transaction_url',
            'name_space'
        )

        validators = []


class ActivitySerializerByIatiIdentifier(ActivitySerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='activities:activity-detail-by-iati-identifier',
        lookup_field='iati_identifier',
        read_only=True
    )


class ActivityDetailSerializer(ActivitySerializer):
    def to_representation(self, instance):
        return super(ActivitySerializer, self).to_representation(
            instance=instance)
