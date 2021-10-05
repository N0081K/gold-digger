from datetime import date
from decimal import Decimal

import pytest

from gold_digger.database.dao_exchange_rate import DaoExchangeRate
from gold_digger.database.dao_provider import DaoProvider


@pytest.fixture
def dao_exchange_rate(db_session):
    """
    :type db_session: sqlalchemy.orm.Session
    :rtype: gold_digger.database.DaoExchangeRate
    """
    return DaoExchangeRate(db_session)


@pytest.fixture
def dao_provider(db_session):
    """
    :type db_session: sqlalchemy.orm.Session
    :rtype: gold_digger.database.DaoProvider
    """
    return DaoProvider(db_session)


@pytest.mark.slow
def test_insert_new_rate(dao_exchange_rate, dao_provider):
    """
    :type dao_exchange_rate: gold_digger.database.DaoExchangeRate
    :type dao_provider: gold_digger.database.DaoProvider
    """
    assert dao_exchange_rate.get_rates_by_date_currency(date.today(), "USD") == []

    provider1 = dao_provider.get_or_create_provider_by_name("test1")
    dao_exchange_rate.insert_new_rate(date.today(), provider1, "USD", Decimal(1))

    assert len(dao_exchange_rate.get_rates_by_date_currency(date.today(), "USD")) == 1

    dao_exchange_rate.insert_new_rate(date.today(), provider1, "USD", Decimal(1))

    assert len(dao_exchange_rate.get_rates_by_date_currency(date.today(), "USD")) == 1


@pytest.mark.slow
def test_insert_exchange_rate_to_db(dao_exchange_rate, dao_provider, logger):
    """
    :type dao_exchange_rate: gold_digger.database.DaoExchangeRate
    :type dao_provider: gold_digger.database.DaoProvider
    :type logger: gold_digger.utils.ContextLogger
    """
    assert dao_exchange_rate.get_rates_by_date_currency(date.today(), "USD") == []

    provider1 = dao_provider.get_or_create_provider_by_name("test1")
    provider2 = dao_provider.get_or_create_provider_by_name("test2")

    records = [
        {"date": date.today(), "currency": "USD", "provider_id": provider1.id, "rate": Decimal(1)},
        {"date": date.today(), "currency": "USD", "provider_id": provider2.id, "rate": Decimal(1)},
        {"date": date.today(), "currency": "USD", "provider_id": provider1.id, "rate": Decimal(1)},
    ]
    dao_exchange_rate.insert_exchange_rate_to_db(records, logger)

    assert len(dao_exchange_rate.get_rates_by_date_currency(date.today(), "USD")) == 2


@pytest.mark.slow
def test_get_sum_of_rates_in_period(dao_exchange_rate, dao_provider):
    """
    :type dao_exchange_rate: gold_digger.database.DaoExchangeRate
    :type dao_provider: gold_digger.database.DaoProvider
    """
    start_date = date(2016, 1, 1)
    end_date = date(2016, 1, 10)
    assert dao_exchange_rate.get_sum_of_rates_in_period(start_date, end_date, "USD") == []

    provider1 = dao_provider.get_or_create_provider_by_name("test1")
    dao_exchange_rate.insert_new_rate(date(2016, 1, 1), provider1, "USD", Decimal(1))
    dao_exchange_rate.insert_new_rate(date(2016, 1, 2), provider1, "USD", Decimal(2))
    dao_exchange_rate.insert_new_rate(date(2016, 1, 3), provider1, "USD", Decimal(3))

    records = dao_exchange_rate.get_sum_of_rates_in_period(start_date, end_date, "USD")
    assert records == [(provider1.id, 3, 6)]
