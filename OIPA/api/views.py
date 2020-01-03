from django.db import OperationalError, connections
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response

# from rest_framework.reverse import reverse


@api_view(('GET',))
def welcome(request, format=None):
    """
    ## REST API

    The REST API provides programmatic access to read (and soon also write)
    IATI data.
    The REST API responses are available in JSON, CSV and XLS for the latter
    two, you can use the 'export_name' api parameter to give them a name
    otherwise it will be given a default name, depending on the endpoint

    ## Available endpoints

    * Activities: [`/api/activities`](/api/activities)

    * Budget aggregations: [`/api/budgets/aggregations`](/api/budgets/aggregations)

    * Codelists: [`/api/publishers`](/api/codelists)

    * Countries: [`/api/countries`](/api/countries)

    * Current branch: [`/api/branch`](/api/branch)

    * Datasets: [`/api/datasets`](/api/datasets)

    * Locations: [`/api/locations`](/api/locations)

    * Organisations: [`/api/organisations`](/api/organisations)

    * Publishers: [`/api/publishers`](/api/publishers)

    * Regions: [`/api/regions`](/api/regions)

    * Results aggregations: [`/api/results/aggregations`](/api/results/aggregations)

    * Sectors: [`/api/sectors`](/api/sectors)

    * Transactions: [`/api/transactions`](/api/transactions)


    ## Info about XLS export

    The XLS export currently works similarly to the way the CSV one works:

    * There's a different way of forming detail results and a list of results:
    If a detail view is requested(something like this:  [`/api/activities/1`](/api/activities/1))
    the data would be formed from all of the json fields, whereas for a multiple result api call
    (something like this:  [`/api/activities`](/api/activities)) the data would be formed only
    from the 'results' field

    * The headers are formed according to the json format of the api call for example for a json like this -
        "title:{ narrative: [ text: 'The actual text' ] }" the column header for the cell 'The actual text'
         would look like this - "title.narratives.0.text"

    Now, when exporting in xls, you may pass in a parameter 'export_fields',
    with this parameter you can specify what do you wish to get in your xls file, and how these fields are named.
    Similarly to the above example the parameter should/could look like this:
    'export_fields={"title.narratives.0.text":"Project title one","title.narratives.1.text":"Project title 2"}'

    #### NOTE: \n
    The easiest way to figure out what fields you want and what to change them to is to just download the
    xls with the default values and form the export_fields parameter from that

    """  # NOQA: E501
    # return Response({
    #     'endpoints': {
    #         'regions': reverse(
    #             'regions:region-list',
    #             request=request,
    #             format=format),
    #         'activities': reverse(
    #             'activities:activity-list',
    #             request=request,
    #             format=format),
    #         'countries': reverse(
    #             'countries:country-list',
    #             request=request,
    #             format=format),
    #         'sectors': reverse(
    #             'sectors:sector-list',
    #             request=request,
    #             format=format),
    #         'organisations': reverse(
    #             'organisations:organisation-list',
    #             request=request,
    #             format=format),
    #         'transactions': reverse(
    #             'transactions:transaction-list',
    #             request=request,
    #             format=format),
    #         'publishers': reverse(
    #             'publishers:publisher-list',
    #             request=request,
    #             format=format),
    #         'datasets': reverse(
    #             'datasets:dataset-list',
    #             request=request,
    #             format=format),
    #         'locations': reverse(
    #             'locations:location-list',
    #             request=request,
    #             format=format),
    #         'results': reverse(
    #             'results:result-aggregations',
    #             request=request,
    #             format=format),
    #         'budgets': reverse(
    #             'budgets:budget-aggregations',
    #             request=request,
    #             format=format),
    #         'codelists': reverse(
    #             'codelists:codelist-meta-list',
    #             request=request,
    #             format=format),
    #         # We remove for now because need implemented
    #         # 'chains': reverse(
    #         #    'chains:chain-list',
    #         #    request=request,
    #         #    format=format),
    #         'branch': reverse(
    #             'branch:current-branch',
    #             request=request,
    #             format=format
    #         )
    #     }
    # })
    return Response(None)


@api_view(('GET',))
def health_check(request, format=None):
    """
    Performs an API health check
    """
    okay = True

    conn = connections['default']
    try:
        conn.cursor()
    except OperationalError:
        okay = False

    if okay is False:
        return Response(status=500)

    return Response(status=200)


def redirect_v1_activity_api(request):
    uri = request.GET.urlencode()
    url = '/api/activities/?' + uri if uri else '/api/activities'
    return redirect(url,  permanent=True)
