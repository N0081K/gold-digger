from datetime import date, datetime

import click
from crontab import CronTab

from . import di_container
from .api_server.app import app
from .database.db_model import Base
from .settings import DATABASE_NAME


def _parse_date(ctx, param, value):
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise click.BadParameter('Date should be in format yyyy-mm-dd')


@click.group()
def cli():
    """
    Define CLI click group.
    """
    pass


@cli.command("cron", help="Run cron jobs")
def cron(**_):
    """
    Run cron jobs.
    """
    with di_container(__file__) as di:
        logger = di.logger()
        cron_tab = CronTab(
            tab="""
                # m h dom mon dow command
                5 0 * * * cd /app && python -m gold_digger update --exclude-providers fixer.io {redirect}
                5 2 * * * cd /app && python -m gold_digger update --providers fixer.io {redirect}
                0 * * * * echo "`date` - cron health check" {redirect}
            """.format(redirect="> /proc/1/fd/1 2>/proc/1/fd/2"),  # redirect to stdout/stderr
        )

        logger.info("Cron started. Commands:\n{}\n---".format("\n".join(list(map(str, cron_tab.crons)))))

        for result in cron_tab.run_scheduler():
            print(result)  # noqa: T001


@cli.command("initialize-db", help="Create empty table (drop if exists)")
def initialize_db(**_):
    """
    Create empty  table (drop if exists).
    """
    with di_container(__file__) as di:
        print("This will drop & create all tables in '%s'. To continue press 'c'" % DATABASE_NAME)  # noqa: T001
        if input() != "c":
            return
        Base.metadata.drop_all(di.db_connection)
        Base.metadata.create_all(di.db_connection)


@cli.command("update-all", help="Update rates since origin date (default 2015-01-01)")
@click.option("--origin-date", default=date(2015, 1, 1), callback=_parse_date, help="Specify date in format 'yyyy-mm-dd'")
def update_all(**kwargs):
    """
    Update rates since origin date (default 2015-01-01).
    """
    with di_container(__file__) as di:
        logger = di.logger()
        di.exchange_rate_manager.update_all_historical_rates(kwargs["origin_date"], logger)


@cli.command("update", help="Update rates of specified day (default today)")
@click.option("--date", default=date.today(), callback=_parse_date, help="Specify date in format 'yyyy-mm-dd'")
@click.option("--providers", type=str, help="Specify data providers names separated by comma.")
@click.option("--exclude-providers", type=str, help="Specify data providers names separated by comma.")
def update(**kwargs):
    """
    Updates rates of specified day (default today).
    """
    with di_container(__file__) as di:
        logger = di.logger()
        if kwargs["providers"]:
            providers = kwargs["providers"].split(",")
        else:
            providers = list(di.data_providers)

        if kwargs["exclude_providers"]:
            excluded_providers = kwargs["exclude_providers"].split(",")
            providers = [p for p in providers if p not in excluded_providers]

        data_providers = [di.data_providers[provider_name] for provider_name in providers]
        di.exchange_rate_manager.update_all_rates_by_date(kwargs["date"], data_providers, logger)


@cli.command("api", help="Run API server (simple)")
@click.option("--host", "-h", default="localhost")
@click.option("--port", "-p", default=8080)
def api(**kwargs):
    """
    Run API server (simple).
    """
    app.simple_server(kwargs["host"], kwargs["port"])


if __name__ == "__main__":
    cli()
