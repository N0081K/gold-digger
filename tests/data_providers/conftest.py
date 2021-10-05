import pytest

from gold_digger.data_providers import CurrencyLayer, Fixer, Frankfurter, Yahoo


@pytest.fixture
def yahoo(base_currency, http_user_agent, currencies):
    """
    :type base_currency: str
    :type http_user_agent: str
    :type currencies: set[str]
    :rtype: gold_digger.data_providers.Yahoo
    """
    return Yahoo(base_currency, http_user_agent, currencies)


@pytest.fixture
def fixer(base_currency, http_user_agent, logger):
    """
    :type base_currency: str
    :type http_user_agent: str
    :type logger: logging.Logger
    :rtype: gold_digger.data_providers.Fixer
    """
    return Fixer(base_currency, http_user_agent, "simple_access_key", logger)


@pytest.fixture
def frankfurter(base_currency, http_user_agent):
    """
    :type base_currency: str
    :type http_user_agent: str
    :rtype: gold_digger.data_providers.Frankfurter
    """
    return Frankfurter(base_currency, http_user_agent)


@pytest.fixture
def currency_layer(base_currency, http_user_agent, logger):
    """
    :type base_currency: str
    :type http_user_agent: str
    :type logger: logging.Logger
    :rtype: gold_digger.data_providers.CurrencyLayer
    """
    return CurrencyLayer(base_currency, http_user_agent, "simple_access_key", logger)
