from datetime import datetime
from iati.models import Activity
from .models import TransactionBalance


def calculated_transaction_balance_for_one_activity(activity):
    # We need this because the cumulative expenditure & total expenditure
    # is not so straightforwardly received from the standard OIPA
    # So we need to check some stuff here according
    # to what Maxime (the responsible person from Unesco) noted

    now = datetime.now()
    total_budget = 0
    total_expenditure = 0
    cumulative_budget = 0
    cumulative_expenditure = 0
    currency = activity.default_currency

    # Calculated total expenditure & cumulative expenditure
    transactions = activity.transaction_set.all()
    for transaction in transactions:
        # Set currency from current transaction
        currency = transaction.currency

        # Cumulative expenditure is  Sum of all transaction type code="4"
        # (whatever the year)
        if transaction.transaction_type_id == '4':
            cumulative_expenditure = \
                cumulative_expenditure + transaction.value

            # Total expenditures is
            # Sum of all if transaction-type code="4"
            # where transaction-date year is current year
            if transaction.value_date.year == now.year:
                total_expenditure = total_expenditure + transaction.value

        # Cumulative budget is Sum of all transaction type code="2"
        # (whatever the year))
        if transaction.transaction_type_id == '2':
            cumulative_budget = cumulative_budget + transaction.value

    # Total Budget is if budget type="1" and status="2"
    # with period start year and period end year are the current year
    budget = activity.budget_set.filter(
        type__code='1', status__code='2',
        period_start__year=now.year, period_end__year=now.year).first()
    if budget:
        total_budget = budget.value

    # Update or create a transaction balance by activity
    # One activity is related to one activity balance

    transaction_balance, created = TransactionBalance.objects.get_or_create(
        activity=activity,
        defaults={
            'currency': currency,
            'total_budget': total_budget,
            'total_expenditure': total_expenditure,
            'cumulative_budget': cumulative_budget,
            'cumulative_expenditure': cumulative_expenditure
        }
    )

    if not created:
        transaction_balance.currency = currency
        transaction_balance.total_budget = total_budget
        transaction_balance.total_expenditure = total_expenditure
        transaction_balance.cumulative_budget = cumulative_budget
        transaction_balance.cumulative_expenditure = cumulative_expenditure
        transaction_balance.save()


def calculated_all_transaction_balance_for_all_activities():

    activities = Activity.objects.all()
    for activity in activities:
        calculated_transaction_balance_for_one_activity(activity=activity)