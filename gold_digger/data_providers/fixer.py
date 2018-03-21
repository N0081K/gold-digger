# -*- coding: utf-8 -*-

from datetime import date, timedelta
from functools import lru_cache

from ._provider import Provider


class Fixer(Provider):
    BASE_URL = "https://api.fixer.io/{date}"
    name = "fixer.io"

    @lru_cache(maxsize=1)
    def get_supported_currencies(self, date_of_exchange):
        """
        :type date_of_exchange: datetime.date
        :rtype: set
        """
        currencies = set()
        response = self._get(self.BASE_URL.format(date=date_of_exchange))
        if response:
            currencies = set(response.json().get("rates").keys())
        if currencies:
            self.logger.debug("Fixer supported currencies: %s", currencies)
        else:
            self.logger.error("Fixer supported currencies not found.")
        return currencies

    def get_by_date(self, date_of_exchange, currency):
        """
        :type date_of_exchange: date
        :type currency: str
        :rtype: decimal.Decimal | None
        """
        date_of_exchange_string = date_of_exchange.strftime("%Y-%m-%d")
        return self._get_by_date(date_of_exchange_string, currency)

    def get_all_by_date(self, date_of_exchange, currencies):
        """
        :type date_of_exchange: date
        :type currencies: list[str]
        :rtype: dict[str, decimal.Decimal]
        """
        self.logger.debug("Fixer.io - get all for date %s", date_of_exchange)
        date_of_exchange_string = date_of_exchange.strftime("%Y-%m-%d")
        day_rates = {}

        url = self.BASE_URL.format(date=date_of_exchange_string)
        response = self._get(url, params={"base": self.base_currency})

        if response:
            try:
                response = response.json()
                for currency in currencies:
                    if currency in response["rates"]:
                        decimal_value = self._to_decimal(response['rates'][currency])
                        if decimal_value is not None:
                            day_rates[currency] = decimal_value
            except Exception:
                self.logger.exception("Fixer.io - Exception while parsing of the HTTP response.")

        return day_rates

    def get_historical(self, origin_date, currencies):
        """
        :type origin_date: date
        :type currencies: list[str]
        :rtype: dict[date, dict[str, decimal.Decimal]]
        """
        date_of_exchange = origin_date
        date_of_today = date.today()
        if date_of_exchange > date_of_today:
            date_of_exchange, date_of_today = date_of_today, date_of_exchange

        step_by_day = timedelta(days=1)
        historical_rates = {}

        while date_of_exchange != date_of_today:
            day_rates = self.get_all_by_date(date_of_exchange, currencies)
            if day_rates:
                historical_rates[date_of_exchange] = day_rates
            date_of_exchange += step_by_day

        return historical_rates

    def _get_by_date(self, date_of_exchange, currency):
        """
        :type date_of_exchange: str
        :type currency: str
        :rtype: decimal.Decimal | None
        """
        self.logger.debug("Requesting Fixer for %s (%s)", currency, date_of_exchange, extra={"currency": currency, "date": date_of_exchange})

        url = self.BASE_URL.format(date=date_of_exchange)
        response = self._get(url, params={"base": self.base_currency, "symbols": currency})
        if response:
            try:
                response = response.json()
                if currency in response["rates"]:
                    return self._to_decimal(response['rates'][currency])

            except Exception:
                self.logger.exception("Fixer.io - Exception while parsing of the HTTP response.")

        return None

    def __str__(self):
        return self.name