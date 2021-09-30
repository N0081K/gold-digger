import logging
from functools import lru_cache
from os.path import abspath, dirname, normpath
from urllib.parse import quote
from uuid import uuid4

import graypy
from cached_property import cached_property as service
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from . import settings
from .data_providers import CurrencyLayer, Fixer, Frankfurter, GrandTrunk, Yahoo
from .database.dao_exchange_rate import DaoExchangeRate
from .database.dao_provider import DaoProvider
from .managers.exchange_rate_manager import ExchangeRateManager
from .utils import ContextLogger
from .utils.custom_logging import IncludeFilter


class DiContainer:
    def __init__(self, main_file_path):
        """
        :type main_file_path: str
        """
        self._file_path = normpath(abspath(main_file_path))

        self._db_connection = None
        self._db_session = None

    def __enter__(self):
        """
        :rtype: gold_digger.di.DiContainer
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        :type exc_type: None | type[BaseException]
        :type exc_val: None | BaseException
        :type exc_tb: None | traceback
        """
        if self._db_session is not None:
            self._db_session.remove()
            self._db_session = None
        if self._db_connection is not None:
            self._db_connection.dispose()
            self._db_connection = None

    @staticmethod
    def flow_id():
        """
        :rtype: str
        """
        return str(uuid4())

    @service
    def base_dir(self):
        """
        :rtype: str
        """
        return dirname(self._file_path)

    @service
    def db_connection(self):
        """
        :rtype: sqlalchemy.engine.base.Engine
        """
        self._db_connection = create_engine("{dialect}://{user}:{password}@{host}:{port}/{name}".format(
            dialect=settings.DATABASE_DIALECT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            name=settings.DATABASE_NAME,
        ))
        return self._db_connection

    @service
    def db_session(self):
        """
        :rtype: sqlalchemy.orm.Session
        """
        self._db_session = scoped_session(sessionmaker(self.db_connection))
        return self._db_session()

    @property
    def base_currency(self):
        """
        :rtype: str
        """
        return "USD"

    @service
    def data_providers(self):
        """
        :rtype: dict[str, gold_digger.data_providers.Provider]
        """
        providers = (
            GrandTrunk(self.base_currency, settings.USER_AGENT_HTTP_HEADER),
            CurrencyLayer(self.base_currency, settings.USER_AGENT_HTTP_HEADER, settings.SECRETS_CURRENCY_LAYER_ACCESS_KEY, self.logger()),
            Yahoo(self.base_currency, settings.USER_AGENT_HTTP_HEADER, settings.SUPPORTED_CURRENCIES),
            Fixer(self.base_currency, settings.USER_AGENT_HTTP_HEADER, settings.SECRETS_FIXER_ACCESS_KEY, self.logger()),
            Frankfurter(self.base_currency, settings.USER_AGENT_HTTP_HEADER),
        )
        return {provider.name: provider for provider in providers}

    @service
    def exchange_rate_manager(self):
        """
        :rtype: gold_digger.managers.exchange_rate_manager.ExchangeRateManager
        """
        return ExchangeRateManager(
            DaoExchangeRate(self.db_session),
            DaoProvider(self.db_session),
            list(self.data_providers.values()),
            self.base_currency,
            settings.SUPPORTED_CURRENCIES,
        )

    @classmethod
    def logger(cls, **extra):
        """
        :type extra: dict
        :rtype: gold_digger.utils.ContextLogger
        """
        logger_ = cls.set_up_logger("gold-digger")
        logger_.setLevel(settings.LOGGING_LEVEL)

        extra_ = {"flow_id": cls.flow_id()}
        if settings.APP_VERSION:
            extra_["version"] = settings.APP_VERSION

        extra_.update(extra or {})

        return ContextLogger(logger_, extra_)

    @staticmethod
    @lru_cache(maxsize=None)
    def add_logger_to_root_filter(name):
        """
        :type name: str
        """
        IncludeFilter(name)

    @classmethod
    @lru_cache(maxsize=None)
    def set_up_logger(cls, name):
        """
        :type name: str
        :rtype: logging.Logger
        """
        logger_ = logging.getLogger(name)
        cls.add_logger_to_root_filter(name)

        return logger_

    @staticmethod
    @lru_cache(maxsize=1)
    def set_up_root_logger():
        """
        Function for setting root logger. Should be called only once.
        """
        logger_ = logging.getLogger()
        if settings.LOGGING_GRAYLOG_ENABLED:
            handler = graypy.GELFRabbitHandler(
                url=f"amqp://{settings.LOGGING_AMQP_USERNAME}:{quote(settings.LOGGING_AMQP_PASSWORD, safe='')}@"
                    f"{settings.LOGGING_AMQP_HOST}:{settings.LOGGING_AMQP_PORT}",
                exchange="gold-digger",
                exchange_type="direct",
                routing_key="gold-digger",
                connect_timeout=10,
                read_timeout=60,
                write_timeout=60,
            )

        else:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(settings.LOGGING_FORMAT, "%Y-%m-%d %H:%M:%S"))

        handler.setLevel(settings.LOGGING_LEVEL)
        handler.addFilter(IncludeFilter())

        logger_.addHandler(handler)
