import pytest

from gold_digger.data_providers import CurrencyLayer, Fixer, Frankfurter, Yahoo


@pytest.fixture
def yahoo(base_currency, currencies):
    return Yahoo(base_currency, currencies)


@pytest.fixture
def fixer(base_currency, logger):
    return Fixer(base_currency, "simple_access_key", logger)


@pytest.fixture
def frankfurter(base_currency):
    return Frankfurter(base_currency)


@pytest.fixture
def currency_layer(base_currency, logger):
    return CurrencyLayer(base_currency, "simple_access_key", logger)
