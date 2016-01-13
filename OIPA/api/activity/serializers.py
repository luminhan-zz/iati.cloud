from rest_framework import serializers

import iati
from api.generics.serializers import DynamicFieldsSerializer
from api.generics.serializers import DynamicFieldsModelSerializer
from api.generics.serializers import FilterableModelSerializer
from api.generics.fields import PointField
from api.sector.serializers import SectorSerializer
from api.region.serializers import RegionSerializer
from api.country.serializers import CountrySerializer
# from api.activity.filters import BudgetFilter
from api.activity.filters import RelatedActivityFilter


class XMLMetaMixin(object):
    def to_representation(self, *args, **kwargs):
        representation = super(XMLMetaMixin, self).to_representation(*args, **kwargs)
        if hasattr(self, 'xml_meta'):
            representation.xml_meta = self.xml_meta
        return representation


# TODO: serialize vocabulary in codelist serializer
class VocabularySerializer(XMLMetaMixin, serializers.Serializer):
    xml_meta = {'only': 'code'}

    code = serializers.CharField()
    name = serializers.CharField()

class CodelistSerializer(XMLMetaMixin, DynamicFieldsSerializer):
    xml_meta = {'only': 'code'}

    code = serializers.CharField()
    name = serializers.CharField()

class CodelistCategorySerializer(CodelistSerializer):
    category = CodelistSerializer()

class CodelistVocabularySerializer(CodelistSerializer):
    vocabulary = VocabularySerializer()

# TODO: separate this
class NarrativeSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('language',)}

    text = serializers.CharField(source="content")
    language = CodelistSerializer()

    class Meta:
        model = iati.models.Narrative
        fields = (
            'text',
            'language',
        )

class NarrativeContainerSerializer(serializers.Serializer):
    narratives = NarrativeSerializer(many=True)


class DocumentCategorySerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('code',)}

    class Meta:
        model = iati.models.DocumentCategory
        fields = ('code', 'name')


class DocumentLinkSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('url', 'format',)}

    format = CodelistSerializer(source='file_format')
    categories = DocumentCategorySerializer(many=True)
    title = NarrativeContainerSerializer(source="documentlinktitle_set", many=True)

    class Meta:
        model = iati.models.DocumentLink
        fields = (
            'url',
            'format',
            'categories',
            'title'
        )


class CapitalSpendSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('percentage',)}

    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        source='capital_spend',
        coerce_to_string=False
    )

    class Meta:
        model = iati.models.Activity
        fields = ('percentage',)


class BudgetSerializer(XMLMetaMixin, FilterableModelSerializer):
    xml_meta = {'attributes': ('type',)}

    class ValueSerializer(serializers.Serializer):
        currency = CodelistSerializer()
        date = serializers.CharField(source='value_date')
        value = serializers.DecimalField(
            max_digits=15,
            decimal_places=2,
            coerce_to_string=False,
        )

        class Meta:
            model = iati.models.Budget
            fields = (
                'value',
                'date',
                'currency',
            )

    value = ValueSerializer(source='*')
    type = CodelistSerializer()

    class Meta:
        model = iati.models.Budget
        # filter_class = BudgetFilter
        fields = (
            'type',
            'period_start',
            'period_end',
            'value',
        )


class ActivityDateSerializer(XMLMetaMixin, serializers.Serializer):
    xml_meta = {'attributes': ('type', 'iso_date')}

    type = CodelistSerializer()
    iso_date = serializers.DateTimeField()

    class Meta:
        model = iati.models.ActivityDate
        fields = ('iso_date', 'type')


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


class ReportingOrganisationSerializer(XMLMetaMixin, DynamicFieldsModelSerializer):
    xml_meta = {'attributes': ('ref', 'type',)}

    # TODO: Link to organisation standard (hyperlinked)
    ref = serializers.CharField(source="normalized_ref")
    type = CodelistSerializer()
    secondary_reporter = serializers.BooleanField()
    narratives = NarrativeSerializer(many=True)

    class Meta:
        model = iati.models.ActivityReportingOrganisation
        fields = (
            'ref',
            'type',
            'secondary_reporter',
            'narratives',
        )

class ParticipatingOrganisationSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('ref', 'type', 'role',)}

    # TODO: Link to organisation standard (hyperlinked)
    ref = serializers.CharField(source='normalized_ref')
    type = CodelistSerializer()
    role = CodelistSerializer()
    narratives = NarrativeSerializer(many=True)

    class Meta:
        model = iati.models.ActivityParticipatingOrganisation
        fields = (
            'ref',
            'type',
            'role',
            'narratives',
        )

class ActivityPolicyMarkerSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('code', 'vocabulary', 'significance',)}

    code = CodelistSerializer()
    vocabulary = VocabularySerializer()
    significance = CodelistSerializer()
    narratives = NarrativeSerializer(many=True)

    class Meta:
        model = iati.models.ActivityPolicyMarker
        fields = (
            'narratives',
            'vocabulary',
            'significance',
            'code',
        )


# TODO: change to NarrativeContainer
class TitleSerializer(serializers.Serializer):
    narratives = NarrativeSerializer(many=True)

    class Meta:
        model = iati.models.Title
        fields = ('narratives',)

class DescriptionSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('type',)}

    type = CodelistSerializer()
    narratives = NarrativeSerializer(many=True)

    class Meta:
        model = iati.models.Description
        fields = (
            'type',
            'narratives'
        )

class RelatedActivityTypeSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('only', 'code')}

    class Meta:
        model = iati.models.RelatedActivityType
        fields = (
            'code',
            'name'
        )

class RelatedActivitySerializer(XMLMetaMixin, FilterableModelSerializer):
    xml_meta = {'attributes': ('ref_activity', 'type')}
    
    ref_activity = serializers.HyperlinkedRelatedField(view_name='activities:activity-detail', read_only=True)
    type = RelatedActivityTypeSerializer()

    class Meta:
        model = iati.models.RelatedActivity
        filter_class = RelatedActivityFilter
        fields = (
            'ref_activity',
            'ref',
            'type',
        )

class ActivitySectorSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('percentage', 'vocabulary')}

    sector = SectorSerializer(fields=('url', 'code', 'name'))
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=False
    )
    vocabulary = VocabularySerializer()

    class Meta:
        model = iati.models.ActivitySector
        fields = (
            'sector',
            'percentage',
            'vocabulary',
        )


class ActivityRecipientRegionSerializer(XMLMetaMixin, DynamicFieldsModelSerializer):
    xml_meta = {'attributes': ('code', 'percentage', 'vocabulary')}

    region = RegionSerializer(
        fields=('url', 'code', 'name')
    )
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=False
    )
    vocabulary = VocabularySerializer()

    class Meta:
        model = iati.models.ActivityRecipientRegion
        fields = (
            'region',
            'percentage',
            'vocabulary',
        )

class RecipientCountrySerializer(XMLMetaMixin, DynamicFieldsModelSerializer):
    xml_meta = {'attributes': ('percentage',)}

    country = CountrySerializer(fields=('url', 'code', 'name'))
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=False
    )
    # vocabulary = VocabularySerializer()

    class Meta:
        model = iati.models.ActivityRecipientCountry
        fields = (
            'country',
            'percentage',
        )


class ResultTypeSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'only': 'code'}

    class Meta:
        model = iati.models.ResultType
        fields = (
            'code',
            'name',
        )

class ResultDescriptionSerializer(serializers.ModelSerializer):
    narratives = NarrativeSerializer(source="*")

    class Meta:
        model = iati.models.ResultDescription
        fields = (
            'narratives',
        )

class ResultTitleSerializer(serializers.ModelSerializer):
    narratives = NarrativeSerializer(source="*")

    class Meta:
        model = iati.models.ResultTitle
        fields = (
            'narratives',
        )

class ResultIndicatorPeriodTargetSerializer(XMLMetaMixin, serializers.Serializer):
    xml_meta = {'attributes': ('value',)}

    value = serializers.CharField(source='target')
    comment = NarrativeContainerSerializer(source="resultindicatorperiodtargetcomment")

class ResultIndicatorPeriodActualSerializer(XMLMetaMixin, serializers.Serializer):
    xml_meta = {'attributes': ('value',)}

    value = serializers.CharField(source='actual')
    comment = NarrativeContainerSerializer(source="resultindicatorperiodactualcomment")

class ResultIndicatorPeriodSerializer(serializers.ModelSerializer):
    target = ResultIndicatorPeriodTargetSerializer(source="*")
    actual = ResultIndicatorPeriodActualSerializer(source="*")

    class Meta:
        model = iati.models.ResultIndicatorPeriod
        fields = (
            'period_start',
            'period_end',
            'target',
            'actual',
        )

class ResultIndicatorBaselineSerializer(XMLMetaMixin, serializers.Serializer):
    xml_meta = {'attributes': ('year', 'value',)}

    year = serializers.CharField(source='baseline_year')
    value = serializers.CharField(source='baseline_value')
    comment = NarrativeContainerSerializer(source="resultindicatorbaselinecomment")

class ResultIndicatorSerializer(serializers.ModelSerializer):
    title = NarrativeContainerSerializer(source="resultindicatortitle")
    description = NarrativeContainerSerializer(source="resultindicatordescription")
    baseline = ResultIndicatorBaselineSerializer(source="*")
    period = ResultIndicatorPeriodSerializer(source='resultindicatorperiod_set', many=True)

    class Meta:
        model = iati.models.ResultIndicator
        fields = (
            'title',
            'description',
            'baseline',
            'period',
        )

class ResultSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('type', 'aggregation_status',)}

    type = CodelistSerializer() 
    title = NarrativeContainerSerializer(source="resulttitle")
    description = NarrativeContainerSerializer(source="resultdescription")
    indicator = ResultIndicatorSerializer(source='resultindicator_set', many=True)

    class Meta:
        model = iati.models.Result
        fields = (
            'title',
            'description',
            'type',
            'aggregation_status',
            'indicator',
        )

class LocationSerializer(XMLMetaMixin, serializers.ModelSerializer):
    xml_meta = {'attributes': ('ref',)}

    class LocationIdSerializer(XMLMetaMixin, serializers.Serializer):
        xml_meta = {'attributes': ('code', 'vocabulary',)}

        vocabulary = VocabularySerializer(
            source='location_id_vocabulary')
        code = serializers.CharField(source='location_id_code')

    class PointSerializer(XMLMetaMixin, serializers.Serializer):
        xml_meta = {'attributes': ('srs_name',)}

        pos = PointField(source='point_pos')
        srs_name = serializers.CharField(source="point_srs_name")

    class AdministrativeSerializer(XMLMetaMixin, serializers.ModelSerializer):
        xml_meta = {'attributes': ('code', 'vocabulary', 'level')}

        code = serializers.CharField()
        vocabulary = VocabularySerializer()

        class Meta:
            model = iati.models.LocationAdministrative
            fields = (
                'code',
                'vocabulary',
                'level',
            )

    location_reach = CodelistSerializer()
    location_id = LocationIdSerializer(source='*')
    name = NarrativeContainerSerializer(many=True, source="locationname_set")
    location_class = CodelistSerializer()
    description = NarrativeContainerSerializer(many=True, source="locationdescription_set")
    activity_description = NarrativeContainerSerializer(many=True, source="locationactivitydescription_set")
    feature_designation = CodelistCategorySerializer()
    administrative = AdministrativeSerializer(many=True, source="locationadministrative_set")
    exactness = CodelistSerializer()
    point = PointSerializer(source="*")

    class Meta:
        model = iati.models.Location
        fields = (
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
        )

class ActivitySerializer(XMLMetaMixin, DynamicFieldsModelSerializer):
    xml_meta = {'attributes': ('default_currency', 'last_updated_datetime', 'linked_data_uri', 'hierarchy',)}

    url = serializers.HyperlinkedIdentityField(view_name='activities:activity-detail')
    last_updated_datetime = serializers.DateTimeField()
    activity_status = CodelistSerializer()
    activity_scope = CodelistSerializer(source='scope')
    capital_spend = CapitalSpendSerializer(source='*')
    collaboration_type = CodelistSerializer()
    default_aid_type = CodelistSerializer()
    default_currency = CodelistSerializer()
    default_finance_type = CodelistSerializer()
    default_flow_type = CodelistSerializer()
    default_tied_status = CodelistSerializer()
    activity_date = ActivityDateSerializer(
        many=True,
        source='activitydate_set')
    reporting_organisation = ReportingOrganisationSerializer(
            many=True,
            source='reporting_organisations')
    participating_organisation = ParticipatingOrganisationSerializer(
        many=True,
        source='participating_organisations')

    # transactions = TransactionSerializer(
    #     many=True,
    #     source='transaction_set'
    # )

    transaction = serializers.HyperlinkedIdentityField(
        view_name='activities:activity-transactions',
    )

    policy_marker = ActivityPolicyMarkerSerializer(
        many=True,
        source='activitypolicymarker_set'
    )
    recipient_country = RecipientCountrySerializer(
        many=True,
        source='activityrecipientcountry_set'
    )
    sector = ActivitySectorSerializer(
        many=True,
        source='activitysector_set'
    )
    recipient_region = ActivityRecipientRegionSerializer(
        many=True,
        source='activityrecipientregion_set'
    )
    budget = BudgetSerializer(many=True, source='budget_set')

    title = TitleSerializer()
    description = DescriptionSerializer(
        many=True, read_only=True, source='description_set')

    document_link = DocumentLinkSerializer(
        many=True,
        source='documentlink_set')
    result = ResultSerializer(many=True, source="result_set")
    location = LocationSerializer(many=True, source='location_set')

    related_activity = RelatedActivitySerializer(many=True, source='relatedactivity_set')

    activity_aggregation = ActivityAggregationSerializer()
    child_aggregation = ActivityAggregationSerializer()
    activity_plus_child_aggregation = ActivityAggregationSerializer()

    class Meta:
        model = iati.models.Activity
        fields = (
            'url',
            'id',
            'iati_identifier',
            'title',
            'description',
            'last_updated_datetime',
            'default_currency',
            'hierarchy',
            'linked_data_uri',
            'reporting_organisation',
            'participating_organisation',
            'related_activity',
            'activity_status',
            'activity_date',
            'activity_scope',
            'recipient_country',
            'recipient_region',
            'sector',
            'transaction',
            'policy_marker',
            'collaboration_type',
            'default_flow_type',
            'default_finance_type',
            'default_aid_type',
            'default_tied_status',
            'budget',
            'capital_spend',
            'xml_source_ref',
            'document_link',
            'result',
            'location',
            'activity_aggregation',
            'child_aggregation',
            'activity_plus_child_aggregation'
        )

