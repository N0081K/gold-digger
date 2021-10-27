# Gold-digger (Exchange rates service)


## Used technologies
 - [Python 3.8.12](https://www.python.org/)
 - [PostgreSQL](http://www.postgresql.org/)


## Development setup

Setup python environment:

```sh
pip install -U pip wheel && pip install -r requirements-dev.txt
```

Create PostgreSQL database `golddigger` and grant permissions to user `postgres`.

```postgresql
CREATE DATABASE "golddigger" WITH OWNER = postgres ENCODING = 'UTF8';
```

Create local settings file called `gold_digger/settings/_settings_local.py` with configuration for local machine.
For development purposes there is no configuration required so file may be empty.

For custom database connection use something like this to overwrite default configuration in `gold_digger/settings/_settings_default.py`:

```python
DATABASE_HOST = "<your_PG_server>"
DATABASE_PORT = "<database_port>"
DATABASE_USER = "<database_user>"
DATABASE_PASSWORD = "<secret_password>"
DATABASE_NAME = "<database_name>"
```


## Usage
Available commands:

* `python -m gold_digger initialize-db` creates all tables in new database
* `python -m gold_digger update [--date="yyyy-mm-dd"]` updates exchange rates for specified date (default today)
* `python -m gold_digger update-all [--origin-date="yyyy-mm-dd"]` updates exchange rates since specified origin date
* `python -m gold_digger api` starts development API server

For running the tests simply use:
* `py.test` or `ptw` which starts watchdog which run the tests after every save of Python file
* `py.test --database-tests --db-connection postgresql://postgres:postgres@localhost/golddigger-test` (with custom db connection) which runs also tests marked as `@database_test`.
 These tests are executed against real test database.

### Tests & QA
- `pytest` runs unit tests (use `--database-tests` for database tests)
- `isort .` sorts imports
- `black .` formats code
- `flake8` checks code quality


## API endpoints

* `/intervals?from=X&to=Y&date=YYYY-MM-DD`
    * from currency - required
    * to currency - required
    * date of exchange - optional; returns last exchange rates if omitted
    * example: [http://localhost:8080/intervals?from=EUR&to=USD&date=2005-12-22](http://localhost:8080/intervals?from=EUR&to=USD&date=2005-12-22)

* `/rate?from=X&to=Y&date=YYYY-MM-DD`
    * from currency - required
    * to currency - required
    * date of exchange - optional; returns last exchange rates if omitted
    * example: [http://localhost:8080/rate?from=EUR&to=USD&date=2005-12-22](http://localhost:8080/rate?from=EUR&to=USD&date=2005-12-22)

* `/range?from=X&to=Y&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
    * from currency - required
    * to currency - required
    * start date & end date of exchange - required
    * example: [http://localhost:8080/range?from=EUR&to=AED&start_date=2016-02-15&end_date=2016-02-15](http://localhost:8080/range?from=EUR&to=AED&start_date=2016-02-15&end_date=2016-02-15)


## Docker

To build a docker image run:

`docker build -t gold-digger:latest .`

Docker container starts the Gunicorn server by default.

* This command runs API container with Gunicorn server:

`docker run --detach --restart=always --publish=8080:8080 --name=gold-digger gold-digger:latest`

* To control Gunicorn's parameters use this:

`docker run --detach --restart=always --publish=8080:8080 -e GUNICORN_WORKERS=1 -e GUNICORN_BIND=0.0.0.0:8080 --name=gold-digger gold-digger:latest`

* To run Cron container with daily updates at 00:05 use command:

`docker run --detach --restart=always --name gold-digger-cron gold-digger:latest python -m gold_digger cron`

* If you are connecting to local database on the host run the container with --net=host option:

`docker run --detach --restart=always --net=host --publish=8080:8080 --name=gold-digger gold-digger:latest`

`docker run --detach --restart=always --net=host --name gold-digger-cron gold-digger:latest python -m gold_digger cron`

* To inject your database user, password, host, port and name use:

```bash
docker run --detach --restart=always \
    -e GOLD_DIGGER_DATABASE_HOST=<your_database_host> \
    -e GOLD_DIGGER_DATABASE_PORT=<your_database_port> \
    -e GOLD_DIGGER_DATABASE_USER=<your_database_user> \
    -e GOLD_DIGGER_DATABASE_PASSWORD=<your_database_secret_password> \
    -e GOLD_DIGGER_DATABASE_NAME=<your_database_name> \
    --publish=8080:8080 --name=gold-digger gold-digger:latest
```

```bash
docker run --detach --restart=always \
    -e GOLD_DIGGER_DATABASE_HOST=<your_database_host> \
    -e GOLD_DIGGER_DATABASE_PORT=<your_database_port> \
    -e GOLD_DIGGER_DATABASE_USER=<your_database_user> \
    -e GOLD_DIGGER_DATABASE_PASSWORD=<your_database_secret_password> \
    -e GOLD_DIGGER_DATABASE_NAME=<your_database_name> \
    --name gold-digger-cron gold-digger:latest python -m gold_digger cron
```


## Settings profiles

Currently, you can use two settings profiles:

* default profile named `local` with definitions in `gold_digger/settings/_settings_local.py`
* production profile named `master` with definitions in `gold_digger/settings/_settings_master.py`

To run this application with production settings `master`  you need to export environment variable `GOLD_DIGGER_PROFILE`.

`docker run --detach --restart=always -e GOLD_DIGGER_PROFILE=master --publish=8080:8080 --name=gold-digger gold-digger:latest`

`docker run --detach --restart=always -e GOLD_DIGGER_PROFILE=master --name gold-digger-cron gold-digger:latest python -m gold_digger cron`
