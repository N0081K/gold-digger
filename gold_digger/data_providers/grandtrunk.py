from collections import defaultdict
from datetime import date, datetime as datetime_
from http import HTTPStatus
from operator import attrgetter

from cachetools import cachedmethod, keys
from requests import RequestException

from ._provider import Provider


class GrandTrunk(Provider):
    """
    Service offers day exchange rates based on Federal Reserve and European Central Bank.
    It is currently free for use in low-volume and non-commercial settings.
    """

    BASE_URL = "http://currencies.apps.grandtrunk.net"
    name = "grandtrunk"

    def __init__(self, base_currency, http_user_agent):
        """
        :type base_currency: str
        :type http_user_agent: str
        """
        super().__init__(base_currency, http_user_agent)

        self.has_request_limit = True

    @cachedmethod(cache=attrgetter("_cache"), key=lambda date_of_exchange, _: keys.hashkey(date_of_exchange))
    @Provider.check_request_limit(return_value=set())
    def get_supported_currencies(self, date_of_exchange, logger):
        """
        :type date_of_exchange: date
        :type logger: gold_digger.utils.ContextLogger
        :rtype: set[str]
        """
        response = self._get(f"{self.BASE_URL}/currencies/{date_of_exchange.strftime('%Y-%m-%d')}", logger=logger)
        if response is None:
            return set()
        if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
            self.set_request_limit_reached(logger)
            return set()
        if response.status_code != HTTPStatus.OK:
            return set()

        currencies = set(response.text.split("\n"))
        if currencies:
            logger.debug("%s - Supported currencies: %s", self, currencies)
        else:
            logger.error("%s - Supported currencies not found.", self)

        return currencies

    @Provider.check_request_limit(return_value=None)
    def get_by_date(self, date_of_exchange, currency, logger):
        """
        :type date_of_exchange: date
        :type currency: str
        :type logger: gold_digger.utils.ContextLogger
        :rtype: decimal.Decimal | None
        """
        date_str = date_of_exchange.strftime("%Y-%m-%d")
        logger.debug("%s - Requesting for %s (%s)", self, currency, date_str, extra={"currency": currency, "date": date_str})

        response = self._get(f"{self.BASE_URL}/getrate/{date_str}/{self.base_currency}/{currency}", logger=logger)
        if response is None:
            return None
        if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
            self.set_request_limit_reached(logger)
            return None
        if response.status_code != HTTPStatus.OK:
            return None

        return self._to_decimal(response.text.strip(), currency, logger=logger)

    @Provider.check_request_limit(return_value={})
    def get_all_by_date(self, date_of_exchange, currencies, logger):
        """
        :type date_of_exchange: date
        :type currencies: set[str]
        :type logger: gold_digger.utils.ContextLogger
        :rtype: dict[str, decimal.Decimal | None]
        """
        logger.debug("%s - Requesting for all rates for date %s", self, date_of_exchange)

        day_rates = {}
        supported_currencies = self.get_supported_currencies(date_of_exchange, logger)
        for currency in currencies:
            if currency not in supported_currencies:
                continue

            response = self._get(f"{self.BASE_URL}/getrate/{date_of_exchange}/{self.base_currency}/{currency}", logger=logger)
            if response is None:
                continue
            if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
                self.set_request_limit_reached(logger)
                return {}
            if response.status_code != HTTPStatus.OK:
                continue

            decimal_value = self._to_decimal(response.text.strip(), currency, logger=logger)
            if decimal_value:
                day_rates[currency] = decimal_value

        return day_rates

    @Provider.check_request_limit(return_value={})
    def get_historical(self, origin_date, currencies, logger):
        """
        :type origin_date: date
        :type currencies: set[str]
        :type logger: gold_digger.utils.ContextLogger
        :rtype: dict[date, dict[str, decimal.Decimal]]
        """
        day_rates = defaultdict(dict)
        origin_date_string = origin_date.strftime("%Y-%m-%d")
        for currency in currencies:
            response = self._get(f"{self.BASE_URL}/getrange/{origin_date_string}/{date.today()}/{self.base_currency}/{currency}", logger=logger)
            if response is None:
                continue
            if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
                self.set_request_limit_reached(logger)
                return {}
            if response.status_code != HTTPStatus.OK:
                continue

            for record in response.text.strip().split("\n"):
                record = record.rstrip()
                if record:
                    try:
                        date_string, exchange_rate_string = record.split(" ")
                        day = datetime_.strptime(date_string, "%Y-%m-%d")
                    except ValueError as e:
                        logger.error("%s - Parsing of rate & date on record '%s' failed: %s", self, record, e)
                        continue
                    decimal_value = self._to_decimal(exchange_rate_string, currency, logger=logger)
                    if decimal_value:
                        day_rates[day][currency] = decimal_value

        return day_rates

    def _get(self, url, params=None, *, logger):
        """
        :type url: str
        :type params: None | dict[str, str]
        :type logger: gold_digger.utils.ContextLogger
        :rtype: requests.Response | None
        """
        try:
            self._http_session.cookies.clear()
            response = self._http_session.get(url, params=params, timeout=self.DEFAULT_REQUEST_TIMEOUT)
            if response.status_code != HTTPStatus.OK:
                logger.error("%s - Status code: %s, URL: %s, Params: %s", self, response.status_code, url, params)
            return response
        except RequestException as e:
            logger.error("%s - Exception: %s, URL: %s, Params: %s", self, e, url, params)

        return None
