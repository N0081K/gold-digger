from collections import defaultdict
from datetime import date, datetime as datetime_
from operator import attrgetter

from cachetools import cachedmethod, keys

from ._provider import Provider


class GrandTrunk(Provider):
    """
    Service offers day exchange rates based on Federal Reserve and European Central Bank.
    It is currently free for use in low-volume and non-commercial settings.
    """

    BASE_URL = "http://currencies.apps.grandtrunk.net"
    name = "grandtrunk"

    @cachedmethod(cache=attrgetter("_cache"), key=lambda _, date_of_exchange, __: keys.hashkey(date_of_exchange))
    def get_supported_currencies(self, date_of_exchange, logger):
        """
        :type date_of_exchange: date
        :type logger: gold_digger.utils.ContextLogger
        :rtype: set[str]
        """
        response = self._get(f"{self.BASE_URL}/currencies/{date_of_exchange.strftime('%Y-%m-%d')}", logger=logger)
        if response is None:
            return set()

        currencies = set(response.text.split("\n"))
        if currencies:
            logger.debug("%s - Supported currencies: %s", self, currencies)
        else:
            logger.error("%s - Supported currencies not found.", self)

        return currencies

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

        return self._to_decimal(response.text.strip(), currency, logger=logger)

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

            decimal_value = self._to_decimal(response.text.strip(), currency, logger=logger)
            if decimal_value:
                day_rates[currency] = decimal_value

        return day_rates

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
