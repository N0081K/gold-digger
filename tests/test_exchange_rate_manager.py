from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock

import pytest

from gold_digger.data_providers import CurrencyLayer, Fixer, GrandTrunk
from gold_digger.database.dao_exchange_rate import DaoExchangeRate
from gold_digger.database.dao_provider import DaoProvider
from gold_digger.database.db_model import ExchangeRate, Provider
from gold_digger.managers.exchange_rate_manager import ExchangeRateManager


@pytest.fixture
def dao_exchange_rate_mock():
    """
    :return: Mock of gold_digger.database.DaoExchangeRate
    """
    return Mock(DaoExchangeRate)


@pytest.fixture
def dao_provider_mock():
    """
    :return: Mock of gold_digger.database.DaoProvider
    """
    mock = Mock(DaoProvider)

    def _get_or_create_provider_by_name(name):
        """
        :type name: str
        :rtype: gold_digger.database.db_model.Provider
        """
        return {
            CurrencyLayer.name: Provider(id=1, name=CurrencyLayer.name),
            GrandTrunk.name: Provider(id=2, name=GrandTrunk.name),
        }.get(name)

    mock.get_or_create_provider_by_name.side_effect = _get_or_create_provider_by_name
    return mock


@pytest.fixture
def currency_layer_mock(currencies):
    """
    :type currencies: set[str]
    :return: Mock of gold_digger.data_providers.CurrencyLayer
    """
    mock = Mock(CurrencyLayer)
    mock.name = CurrencyLayer.name
    mock.get_all_by_date.return_value = {"EUR": Decimal(0.77), "USD": Decimal(1)}
    mock.get_supported_currencies.return_value = currencies
    mock.has_request_limit = True
    return mock


@pytest.fixture
def fixer_mock(currencies):
    """
    :type currencies: set[str]
    :return: Mock of gold_digger.data_providers.Fixer
    """
    mock = Mock(Fixer)
    mock.name = Fixer.name
    mock.get_supported_currencies.return_value = currencies
    mock.has_request_limit = True
    return mock


@pytest.fixture
def grandtrunk_mock(currencies):
    """
    :type currencies: set[str]
    :return: Mock of gold_digger.data_providers.GrandTrunk
    """
    mock = Mock(GrandTrunk)
    mock.name = GrandTrunk.name
    mock.get_all_by_date.return_value = {"EUR": Decimal(0.75), "USD": Decimal(1)}
    mock.get_supported_currencies.return_value = currencies
    mock.has_request_limit = False
    return mock


def test_update_all_rates_by_date(dao_exchange_rate_mock, dao_provider_mock, currency_layer_mock, base_currency, currencies, logger):
    """
    Update rates of all providers for the specified date.

    :param dao_exchange_rate_mock: Mock of gold_digger.database.DaoExchangeRate
    :param dao_provider_mock: Mock of gold_digger.database.DaoProvider
    :param currency_layer_mock: Mock of gold_digger.data_providers.CurrencyLayer
    :type base_currency: str
    :type currencies: set[str]
    :type logger: gold_digger.utils.ContextLogger
    """
    _date = date(2016, 2, 17)

    exchange_rate_manager = ExchangeRateManager(dao_exchange_rate_mock, dao_provider_mock, [currency_layer_mock], base_currency, currencies)
    exchange_rate_manager.update_all_rates_by_date(_date, [currency_layer_mock], logger)

    (actual_records, _), _ = dao_exchange_rate_mock.insert_exchange_rate_to_db.call_args
    (provider_name,), _ = dao_provider_mock.get_or_create_provider_by_name.call_args

    assert provider_name == currency_layer_mock.name
    assert sorted(actual_records, key=lambda x: x["currency"]) == [
        {"provider_id": 1, "date": _date, "currency": "EUR", "rate": Decimal(0.77)},
        {"provider_id": 1, "date": _date, "currency": "USD", "rate": Decimal(1)},
    ]


def test_get_or_update_rate_by_date(dao_exchange_rate_mock, dao_provider_mock, currency_layer_mock, grandtrunk_mock, base_currency, currencies, logger):
    """
    Get all rates by date.

    Case: 2 providers, rate of provider 'currency_layer' is in DB, rate of provider 'grandtrunk' miss.
          Get rate for missing provider and update DB. Finally return list of all rates of the day (all provider rates).

    :param dao_exchange_rate_mock: Mock of gold_digger.database.DaoExchangeRate
    :param dao_provider_mock: Mock of gold_digger.database.DaoProvider
    :param currency_layer_mock: Mock of gold_digger.data_providers.CurrencyLayer
    :param grandtrunk_mock: Mock of gold_digger.data_providers.GrandTrunk
    :type base_currency: str
    :type currencies: set[str]
    :type logger: gold_digger.utils.ContextLogger
    """
    _date = date(2016, 2, 17)

    exchange_rate_manager = ExchangeRateManager(dao_exchange_rate_mock, dao_provider_mock, [currency_layer_mock, grandtrunk_mock], base_currency, currencies)

    grandtrunk_mock.get_by_date.return_value = Decimal(0.75)
    dao_exchange_rate_mock.get_rates_by_date_currency.return_value = [
        ExchangeRate(provider=Provider(name=CurrencyLayer.name), date=_date, currency="EUR", rate=Decimal(0.77)),
    ]
    dao_exchange_rate_mock.insert_new_rate.return_value = [
        ExchangeRate(provider=Provider(name=GrandTrunk.name), date=_date, currency="EUR", rate=Decimal(0.75)),
    ]

    exchange_rates = exchange_rate_manager.get_or_update_rate_by_date(_date, currency="EUR", logger=logger)
    insert_new_rate_args, _ = dao_exchange_rate_mock.insert_new_rate.call_args

    assert dao_exchange_rate_mock.insert_new_rate.call_count == 1
    assert insert_new_rate_args[1].name == GrandTrunk.name
    assert len(exchange_rates) == 2


def test_get_or_update_rate_by_date__today_after_cron_update(
    dao_exchange_rate_mock,
    dao_provider_mock,
    currency_layer_mock,
    grandtrunk_mock,
    base_currency,
    currencies,
    logger,
):
    """
    Get all rates by date.

    Case: 2 providers, both rates are in DB as well as yesterday's data. No requests for yesterday should be made.

    :param dao_exchange_rate_mock: Mock of gold_digger.database.DaoExchangeRate
    :param dao_provider_mock: Mock of gold_digger.database.DaoProvider
    :param currency_layer_mock: Mock of gold_digger.data_providers.CurrencyLayer
    :param grandtrunk_mock: Mock of gold_digger.data_providers.GrandTrunk
    :type base_currency: str
    :type currencies: set[str]
    :type logger: gold_digger.utils.ContextLogger
    """
    today = date.today()

    exchange_rate_manager = ExchangeRateManager(dao_exchange_rate_mock, dao_provider_mock, [currency_layer_mock, grandtrunk_mock], base_currency, currencies)

    grandtrunk_mock.get_by_date.return_value = Decimal(0.75)
    dao_exchange_rate_mock.get_rates_by_date_currency.return_value = [
        ExchangeRate(provider=Provider(name=CurrencyLayer.name), date=today, currency="EUR", rate=Decimal(0.77)),
        ExchangeRate(provider=Provider(name=GrandTrunk.name), date=today, currency="EUR", rate=Decimal(0.75)),
    ]
    dao_exchange_rate_mock.get_rate_by_date_currency_provider.return_value = []

    exchange_rates = exchange_rate_manager.get_or_update_rate_by_date(today, currency="EUR", logger=logger)

    assert dao_exchange_rate_mock.get_rate_by_date_currency_provider.call_count == 0
    assert len(exchange_rates) == 2


def test_get_or_update_rate_by_date__today_before_cron_update(
    dao_exchange_rate_mock,
    dao_provider_mock,
    currency_layer_mock,
    grandtrunk_mock,
    base_currency,
    currencies,
    logger,
):
    """
    Get all rates by date.

    Case: 2 providers, rate of provider 'currency_layer' is in DB, rate of provider 'grandtrunk' miss, the date is today, yesterday's rates are in DB.
          Get rate for missing provider from yesterday. Finally return list of all rates of the day (all provider rates).

    :param dao_exchange_rate_mock: Mock of gold_digger.database.DaoExchangeRate
    :param dao_provider_mock: Mock of gold_digger.database.DaoProvider
    :param currency_layer_mock: Mock of gold_digger.data_providers.CurrencyLayer
    :param grandtrunk_mock: Mock of gold_digger.data_providers.GrandTrunk
    :type base_currency: str
    :type currencies: set[str]
    :type logger: gold_digger.utils.ContextLogger
    """
    today = date.today()
    yesterday = today - timedelta(1)

    exchange_rate_manager = ExchangeRateManager(dao_exchange_rate_mock, dao_provider_mock, [currency_layer_mock, grandtrunk_mock], base_currency, currencies)

    grandtrunk_mock.get_by_date.return_value = Decimal(0.75)
    dao_exchange_rate_mock.get_rates_by_date_currency.return_value = [
        ExchangeRate(provider=Provider(name=CurrencyLayer.name), date=today, currency="EUR", rate=Decimal(0.77)),
    ]
    dao_exchange_rate_mock.get_rate_by_date_currency_provider.return_value = [
        ExchangeRate(provider=Provider(name=GrandTrunk.name), date=yesterday, currency="EUR", rate=Decimal(0.75)),
    ]

    exchange_rates = exchange_rate_manager.get_or_update_rate_by_date(today, currency="EUR", logger=logger)

    assert dao_exchange_rate_mock.get_rate_by_date_currency_provider.call_count == 1
    assert dao_exchange_rate_mock.get_rate_by_date_currency_provider.call_args[0] == (yesterday, "EUR", GrandTrunk.name)
    assert len(exchange_rates) == 2


def test_get_or_update_rate_by_date__today_before_cron_update_no_yesterday_rates(
    dao_exchange_rate_mock,
    dao_provider_mock,
    currency_layer_mock,
    grandtrunk_mock,
    base_currency,
    currencies,
    logger,
):
    """
    Get all rates by date.

    Case: 2 providers, rate of provider 'currency_layer' is in DB, rate of provider 'grandtrunk' miss, the date is today, yesterday's rates aren't in DB.
          Try to get rate for missing provider from yesterday, fail and request from API, store to DB.
          Finally return list of all rates of the day (all provider rates).

    :param dao_exchange_rate_mock: Mock of gold_digger.database.DaoExchangeRate
    :param dao_provider_mock: Mock of gold_digger.database.DaoProvider
    :param currency_layer_mock: Mock of gold_digger.data_providers.CurrencyLayer
    :param grandtrunk_mock: Mock of gold_digger.data_providers.GrandTrunk
    :type base_currency: str
    :type currencies: set[str]
    :type logger: gold_digger.utils.ContextLogger
    """
    today = date.today()
    yesterday = today - timedelta(1)

    exchange_rate_manager = ExchangeRateManager(dao_exchange_rate_mock, dao_provider_mock, [currency_layer_mock, grandtrunk_mock], base_currency, currencies)

    grandtrunk_mock.get_by_date.return_value = Decimal(0.75)
    dao_exchange_rate_mock.get_rates_by_date_currency.return_value = [
        ExchangeRate(provider=Provider(name=CurrencyLayer.name), date=today, currency="EUR", rate=Decimal(0.77)),
    ]
    dao_exchange_rate_mock.get_rate_by_date_currency_provider.return_value = []
    dao_exchange_rate_mock.insert_new_rate.return_value = [
        ExchangeRate(provider=Provider(name=GrandTrunk.name), date=today, currency="EUR", rate=Decimal(0.75)),
    ]

    exchange_rates = exchange_rate_manager.get_or_update_rate_by_date(today, currency="EUR", logger=logger)
    insert_new_rate_args, _ = dao_exchange_rate_mock.insert_new_rate.call_args

    assert dao_exchange_rate_mock.insert_new_rate.call_count == 1
    assert insert_new_rate_args[1].name == GrandTrunk.name
    assert dao_exchange_rate_mock.get_rate_by_date_currency_provider.call_count == 1
    assert dao_exchange_rate_mock.get_rate_by_date_currency_provider.call_args[0] == (yesterday, "EUR", GrandTrunk.name)
    assert len(exchange_rates) == 2


def test_get_or_update_rate_by_date__no_api_requests_for_historical_data_on_limited_providers(
    dao_exchange_rate_mock,
    dao_provider_mock,
    fixer_mock,
    currency_layer_mock,
    grandtrunk_mock,
    base_currency,
    currencies,
    logger,
):
    """
    In case historical data are requested and they are not in database we don't want to request API if the provider has request limit.

    :param dao_exchange_rate_mock: Mock of gold_digger.database.DaoExchangeRate
    :param dao_provider_mock: Mock of gold_digger.database.DaoProvider
    :param fixer_mock: Mock of gold_digger.data_providers.Fixer
    :param currency_layer_mock: Mock of gold_digger.data_providers.CurrencyLayer
    :param grandtrunk_mock: Mock of gold_digger.data_providers.GrandTrunk
    :type base_currency: str
    :type currencies: set[str]
    :type logger: gold_digger.utils.ContextLogger
    """
    yesterday = date.today() - timedelta(1)  # yesterday's rates are treated as historical rates

    exchange_rate_manager = ExchangeRateManager(
        dao_exchange_rate_mock,
        dao_provider_mock,
        [fixer_mock, currency_layer_mock, grandtrunk_mock],
        base_currency,
        currencies,
    )

    dao_exchange_rate_mock.get_rates_by_date_currency.return_value = []

    exchange_rates = exchange_rate_manager.get_or_update_rate_by_date(yesterday, currency="EUR", logger=logger)

    assert dao_exchange_rate_mock.get_rates_by_date_currency.call_count == 1
    assert dao_exchange_rate_mock.get_rate_by_date_currency_provider.call_count == 0
    assert grandtrunk_mock.get_by_date.call_count == 1
    assert currency_layer_mock.get_by_date.call_count == 0
    assert fixer_mock.get_by_date.call_count == 0
    assert len(exchange_rates) == 1


def test_get_exchange_rate_by_date(dao_exchange_rate_mock, dao_provider_mock, base_currency, logger):
    """
    :param dao_exchange_rate_mock: Mock of gold_digger.database.DaoExchangeRate
    :param dao_provider_mock: Mock of gold_digger.database.DaoProvider
    :type base_currency: str
    :type logger: gold_digger.utils.ContextLogger
    """
    _date = date(2016, 2, 17)

    exchange_rate_manager = ExchangeRateManager(dao_exchange_rate_mock, dao_provider_mock, [], base_currency, set())

    def _get_rates_by_date_currency(_, currency):
        """
        :type currency: str
        :rtype: list[gold_digger.database.db_model.ExchangeRate]
        """
        return {
            "EUR": [ExchangeRate(id=1, currency="EUR", rate=Decimal(0.89), provider=Provider(name=CurrencyLayer.name))],
            "CZK": [ExchangeRate(id=2, currency="CZK", rate=Decimal(24.20), provider=Provider(name=CurrencyLayer.name))],
        }.get(currency)

    dao_exchange_rate_mock.get_rates_by_date_currency.side_effect = _get_rates_by_date_currency
    exchange_rate = exchange_rate_manager.get_exchange_rate_by_date(_date, "EUR", "CZK", logger)

    assert exchange_rate == Decimal(24.20) / Decimal(0.89)


def test_get_average_exchange_rate_by_dates(dao_exchange_rate_mock, dao_provider_mock, base_currency, logger):
    """
    Get average exchange rate within specified period.

    Case: 10 days period, 10 'EUR' rates but only 9 'CZK' rates in DB, 1 provider
          exchange rate is computed as average rate within the period and 'warning' is logged for missing 'CZK' rate

    :param dao_exchange_rate_mock: Mock of gold_digger.database.DaoExchangeRate
    :param dao_provider_mock: Mock of gold_digger.database.DaoProvider
    :type base_currency: str
    :type logger: gold_digger.utils.ContextLogger
    """
    _start_date = date(2016, 2, 7)
    _end_date = date(2016, 2, 17)

    logger_mock = Mock(logger)
    exchange_rate_manager = ExchangeRateManager(dao_exchange_rate_mock, dao_provider_mock, [], base_currency, set())

    def _get_sum_of_rates_in_period(_, __, currency):
        return {
            "EUR": [[Provider(name=CurrencyLayer.name), 11, Decimal(8.9)]],
            "CZK": [[Provider(name=CurrencyLayer.name), 9, Decimal(217.8)]],
        }.get(currency)

    dao_exchange_rate_mock.get_sum_of_rates_in_period.side_effect = _get_sum_of_rates_in_period

    exchange_rate = exchange_rate_manager.get_average_exchange_rate_by_dates(_start_date, _end_date, "EUR", "CZK", logger_mock)
    eur_average = Decimal(8.9) / 11
    czk_average = Decimal(217.8) / 9

    assert exchange_rate == czk_average * (1 / eur_average)
    assert logger_mock.warning.call_count == 1


def test_pick_rate_from_any_provider_if_rates_are_same():
    """
    Picked exchange rate is the same as the equal candidates.
    """
    best = ExchangeRateManager.pick_the_best([Decimal(0.5), Decimal(0.5), Decimal(0.5)])

    assert best == 0.5


def test_pick_middle_rate_if_it_exists():
    """
    Picked exchange rate is the middle of the unique candidates.
    """
    best = ExchangeRateManager.pick_the_best([Decimal(0.0), Decimal(0.5), Decimal(1.0)])

    assert best == 0.5


def test_pick_middle_rate_if_it_exists2():
    """
    Picked exchange rate is the middle of the unique candidates.
    """
    best = ExchangeRateManager.pick_the_best([Decimal(1.5), Decimal(0.5), Decimal(1.0)])

    assert best == 1.0


def test_pick_rate_from_pair_of_same_rates_by_order_of_providers():
    """
    Picked exchange rate is the most common of the candidates.
    """
    best = ExchangeRateManager.pick_the_best([Decimal(0.0), Decimal(0.7), Decimal(0.7)])

    assert best == 0.7


def test_pick_rate_from_most_similar_pair_of_rates_by_order_of_providers():
    """
    Picked exchange rate is the one most similar to the other candidates.
    """
    best = ExchangeRateManager.pick_the_best([Decimal(0.02), Decimal(0.72), Decimal(0.74)])

    assert best == 0.72


def test_get_exchange_rate_in_intervals_by_date(dao_exchange_rate_mock, dao_provider_mock, base_currency, currencies, logger):
    """
    :param dao_exchange_rate_mock: Mock of gold_digger.database.DaoExchangeRate
    :param dao_provider_mock: Mock of gold_digger.database.DaoProvider
    :type base_currency: str
    :type currencies: set[str]
    :type logger: gold_digger.utils.ContextLogger
    """
    date_of_exchange_ = date(2020, 11, 30)
    start_date_6_days_ago = date_of_exchange_ - timedelta(days=6)
    start_date_30_days_ago = date_of_exchange_ - timedelta(days=30)
    provider = Provider(name=CurrencyLayer.name)
    rates = {
        "EUR": [ExchangeRate(provider=provider, date=date_of_exchange_, currency="EUR", rate=Decimal(10.0))],
        "CZK": [ExchangeRate(provider=provider, date=date_of_exchange_, currency="CZK", rate=Decimal(15.0))],
    }
    sum_of_rates = {
        "EUR": {
            date_of_exchange_: [(provider, 1, Decimal(10.0))],
            start_date_6_days_ago: [(provider, 7, Decimal(70.0))],
            start_date_30_days_ago: [(provider, 31, Decimal(310.0))],
        },
        "CZK": {
            date_of_exchange_: [(provider, 1, Decimal(15.0))],
            start_date_6_days_ago: [(provider, 7, Decimal(140.0))],
            start_date_30_days_ago: [(provider, 31, Decimal(775.0))],
        },
    }
    dao_exchange_rate_mock.get_sum_of_rates_in_period.side_effect = lambda start_date, _, currency: sum_of_rates[currency][start_date]
    dao_exchange_rate_mock.get_rates_by_date_currency.side_effect = lambda _, currency: rates[currency]
    exchange_rate_manager = ExchangeRateManager(dao_exchange_rate_mock, dao_provider_mock, [provider], base_currency, currencies)

    exchange_rate_in_intervals = exchange_rate_manager.get_exchange_rate_in_intervals_by_date(date_of_exchange_, "EUR", "CZK", logger)

    assert exchange_rate_in_intervals == [
        {
            "interval": "daily",
            "exchange_rate": "1.5",
        },
        {
            "interval": "weekly",
            "exchange_rate": "2.0",
        },
        {
            "interval": "monthly",
            "exchange_rate": "2.5",
        },
    ]
