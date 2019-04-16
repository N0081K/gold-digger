# -*- coding: utf-8 -*-

import pytest

from gold_digger.data_providers import Fixer, Yahoo, RatesAPI


@pytest.fixture
def yahoo(base_currency, currencies):
    return Yahoo(base_currency, currencies)


@pytest.fixture
def fixer(base_currency, logger):
    return Fixer("simple_access_key", logger, base_currency)


@pytest.fixture
def rates_api(base_currency):
    return RatesAPI(base_currency)
