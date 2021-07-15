import pytest

from gold_digger.data_providers import CurrencyLayer, Fixer, Frankfurter, Yahoo


@pytest.fixture
def yahoo(base_currency, http_user_agent, currencies):
    return Yahoo(base_currency, http_user_agent, currencies)


@pytest.fixture
def fixer(base_currency, http_user_agent, logger):
    return Fixer(base_currency, http_user_agent, "simple_access_key", logger)


@pytest.fixture
def frankfurter(base_currency, http_user_agent):
    return Frankfurter(base_currency, http_user_agent)


@pytest.fixture
def currency_layer(base_currency, http_user_agent, logger):
    return CurrencyLayer(base_currency, http_user_agent, "simple_access_key", logger)
