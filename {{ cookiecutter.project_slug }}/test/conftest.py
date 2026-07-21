# Copyright (c) 2026 SURF, GÉANT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import contextlib
import datetime
import ipaddress
import logging
import os
from operator import itemgetter
from pathlib import Path
from uuid import UUID

import orchestrator
import pytest
from alembic import command
from alembic.config import Config
from faker import Faker
from faker.providers import BaseProvider
from oauth2_lib.settings import oauth2lib_settings
from orchestrator.core import app_settings, step
from orchestrator.core.db import (
    Database,
    ProductBlockTable,
    ProductTable,
    ResourceTypeTable,
    SubscriptionMetadataTable,
    WorkflowTable,
    db,
)
from orchestrator.core.db.database import ENGINE_ARGUMENTS, SESSION_ARGUMENTS, BaseModel
from orchestrator.core.domain import SUBSCRIPTION_MODEL_REGISTRY, SubscriptionModel
from orchestrator.core.domain.base import ProductBlockModel
from orchestrator.core.types import SubscriptionLifecycle
from pydantic import PostgresDsn
from pydantic_forms.types import UUIDstr, strEnum
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import scoped_session, sessionmaker
from starlette.testclient import TestClient
from urllib3_mock import Responses

from test import DEFAULT_START_DATE
from test.fixtures import *  # noqa: F403

logger = logging.getLogger("faker.factory")
logger.setLevel(logging.WARNING)


def pytest_configure(config):
    """Set an environment variable before loading any test modules."""
    # Set environment variables for the test session
    os.environ["TESTING"] = "true"

    # Register finalisers to clean up after tests are done
    def cleanup() -> None:
        del os.environ["TESTING"]

    pytest.session_cleanup = cleanup  # ty: ignore[unresolved-attribute]


class FakerProvider(BaseProvider):
    def uuid(self) -> UUID:
        """Return a faker UUID4 string wrapped in a UUID object to avoid IDE type hint warning."""
        return UUID(self.generator.uuid4())

    def ipv4_network(self, *, min_subnet=1, max_subnet=32) -> ipaddress.IPv4Network:
        subnet = str(self.generator.random_int(min=min_subnet, max=max_subnet))
        ipv4 = self.generator.ipv4()
        interface = ipaddress.IPv4Interface(ipv4 + "/" + subnet)
        # Extra step for converting `10.53.92.39/24` to `10.53.92.0/24`
        network = interface.network.network_address

        return ipaddress.IPv4Network(str(network) + "/" + subnet)

    def ipv6_network(self, *, min_subnet=1, max_subnet=128) -> ipaddress.IPv6Network:
        subnet = str(self.generator.random_int(min=min_subnet, max=max_subnet))
        ipv6 = self.generator.ipv6()
        interface = ipaddress.IPv6Interface(ipv6 + "/" + subnet)
        network = interface.network.network_address

        return ipaddress.IPv6Network(str(network) + "/" + subnet)

    def site_name(self) -> str:
        """A random site (PoP) name, formatted as three capitals and sometimes one digit."""
        site_name = "".join(self.generator.random_letter().upper() for _ in range(3))

        if self.generator.boolean():
            digit = self.generator.random_int(min=1, max=9)
            site_name += str(digit)

        return site_name

    def ipv4_netmask(self) -> int:
        return self.generator.random_int(min=1, max=32)

    def ipv6_netmask(self) -> int:
        return self.generator.random_int(min=1, max=128)

    def nokia_physical_interface_name(self) -> str:
        return self.generator.numerify("1/x1/%/c@%/%")

    def juniper_physical_interface_name(self) -> str:
        interface = self.generator.random_choices(elements=("ge", "et", "xe"))[0]
        number = self.generator.numerify("-%/@%/@%")
        return f"{interface}{number}"

    def nokia_lag_interface_name(self) -> str:
        return self.generator.numerify("lag-@%")

    def juniper_ae_interface_name(self) -> str:
        return self.generator.numerify("ae@%")

    def vlan_id(self) -> int:
        return self.generator.random_int(min=1, max=4095)

    def bandwidth(self) -> str:
        bandwidth_value = self.generator.random_int(1, 1000)
        unit = self.generator.random_choices(elements=("K", "M", "G", "T"))[0]
        return f"{bandwidth_value}{unit}"

    def ttl(self) -> int:
        return self.generator.random_int(min=1, max=255)


@pytest.fixture(scope="session")
def faker() -> Faker:
    fake = Faker()
    fake.add_provider(FakerProvider)
    return fake


@pytest.fixture(autouse=True)
def _clear_faker_uniqueness(faker):
    """Reset the already seen values generated by faker.

    The generators in Faker that require uniqueness, only do so on a per-test basis. Therefore, we can reset this after
    every test to avoid `UniquenessException`s."""
    faker.unique.clear()


@pytest.fixture(scope="session")
def db_uri():
    """Provide a unique database URI for each pytest-xdist worker, or a default URI if running without xdist."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER")
    database_host = os.getenv("DATABASE_HOST", "localhost")

    if worker_id:
        return f"postgresql://nwa:nwa@{database_host}/gso-test-db_{worker_id}"

    return os.environ.get("DATABASE_URI_TEST", f"postgresql://nwa:nwa@{database_host}/gso-test-db")


def run_migrations(db_uri: PostgresDsn) -> None:
    """Configure the alembic migration and run the migration on the database.

    Args:
        db_uri: The database uri configuration to run the migration on.

    Returns:
        None
    """
    path = Path(__file__).resolve().parent
    app_settings.DATABASE_URI = db_uri  # ty: ignore[invalid-assignment]
    alembic_cfg = Config(file_=path / "../gso/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(db_uri))

    alembic_cfg.set_main_option("script_location", str(path / "../gso/migrations"))
    version_locations = alembic_cfg.get_main_option("version_locations")
    alembic_cfg.set_main_option(
        "version_locations",
        f"{version_locations} ../../orchestrator/core/migrations/versions/schema",
    )

    command.upgrade(alembic_cfg, "heads")


@pytest.fixture(scope="session")
def _database(db_uri):
    """Create database and run migrations and cleanup afterwards.

    Args:
        db_uri: The database uri configuration to run the migration on.
    """
    db.update(Database(db_uri))  # ty: ignore[unresolved-attribute]
    url = make_url(db_uri)
    db_to_create = url.database
    url = url.set(database="postgres")

    engine = create_engine(url)
    with engine.connect() as conn:
        conn.execute(
            text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:db_name").bindparams(
                db_name=db_to_create,
            ),
        )
        conn.commit()
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(text(f'DROP DATABASE IF EXISTS "{db_to_create}";'))
        conn.commit()
        conn.execute(text(f'CREATE DATABASE "{db_to_create}";'))

    run_migrations(db_uri)
    db.wrapped_database.engine = create_engine(db_uri, **ENGINE_ARGUMENTS)  # ty: ignore[unresolved-attribute]

    try:
        yield
    finally:
        db.wrapped_database.engine.dispose()  # ty: ignore[unresolved-attribute]
        with engine.connect() as conn:
            conn.execute(
                text(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db_to_create}';"),  # noqa: S608
            )
            conn.commit()
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                text(f'DROP DATABASE IF EXISTS "{db_to_create}";')
            )


@pytest.fixture(autouse=True)
def _db_session(_database):
    """Ensure that tests are executed within a transactional scope that automatically rolls back after completion.

    This fixture facilitates a pattern known as 'transactional tests'. At the start, it establishes a connection and
    begins an overarching transaction. Any database operations performed within the test function—whether they commit
    or not happen within the context of this master transaction.

    From the perspective of the test function, it seems as though changes are getting committed to the database,
    enabling the tests to query and assert the persistence of data. Yet, once the test completes, this fixture
    intervenes to roll back the master transaction. This ensures a clean slate after each test, preventing tests from
    polluting the database state for subsequent tests.

    Benefits:
    - Each test runs in isolation with a pristine database state.
    - Avoids the overhead of recreating the database schema or re-seeding data between tests.

    Args:
        _database: A fixture reference that initialises the database.
    """
    with contextlib.closing(db.wrapped_database.engine.connect()) as test_connection:  # ty: ignore[unresolved-attribute]
        # Create a new session factory for this context.
        session_factory = sessionmaker(bind=test_connection, **SESSION_ARGUMENTS)  # ty: ignore[no-matching-overload]
        scoped_session_instance = scoped_session(
            session_factory,
            scopefunc=db.wrapped_database._scopefunc,  # noqa: SLF001  # ty: ignore[unresolved-attribute]
        )

        # Point the database session to this new scoped session.
        db.wrapped_database.session_factory = session_factory  # ty: ignore[unresolved-attribute]
        db.wrapped_database.scoped_session = scoped_session_instance  # ty: ignore[unresolved-attribute]

        # Set the query for the base model.
        BaseModel.set_query(scoped_session_instance.query_property())  # ty: ignore[invalid-argument-type]
        transaction = test_connection.begin()
        try:
            yield
        finally:
            try:
                db.wrapped_database.scoped_session.close_all()  # ty: ignore[unresolved-attribute]
            except Exception:
                logger.exception("Closing wrapped db failed, test teardown may fail")
            if not transaction._deactivated_from_connection:  # noqa: SLF001
                transaction.rollback()


@pytest.fixture(scope="session", autouse=True)
def fastapi_app(_database, db_uri):
    """Load the {{ cookiecutter.project_name }} FastAPI app for testing purposes.

    This implementation is as close as possible to the one present in orchestrator-core.
    """
    from {{ cookiecutter.project_slug }}.main import app

    oauth2lib_settings.OAUTH2_ACTIVE = False
    oauth2lib_settings.ENVIRONMENT_IGNORE_MUTATION_DISABLED = ["local", "TESTING"]
    app_settings.DATABASE_URI = db_uri

    return app


@pytest.fixture(scope="session")
def test_client(fastapi_app):
    return TestClient(fastapi_app)


@pytest.fixture
def generic_resource_type_1():
    rt = ResourceTypeTable(description="Resource Type one", resource_type="rt_1")
    db.session.add(rt)
    db.session.commit()

    return rt


@pytest.fixture
def generic_resource_type_2():
    rt = ResourceTypeTable(description="Resource Type two", resource_type="rt_2")
    db.session.add(rt)
    db.session.commit()
    return rt


@pytest.fixture
def generic_resource_type_3():
    rt = ResourceTypeTable(description="Resource Type three", resource_type="rt_3")
    db.session.add(rt)
    db.session.commit()

    return rt


@pytest.fixture
def generic_product_block_1(generic_resource_type_1):
    pb = ProductBlockTable(
        name="PB_1",
        description="Generic Product Block 1",
        tag="PB1",
        status="active",
        resource_types=[generic_resource_type_1],
        created_at=datetime.datetime.fromisoformat("2023-05-24T00:00:00+00:00"),
    )
    db.session.add(pb)
    db.session.commit()
    return pb


@pytest.fixture
def generic_product_block_2(generic_resource_type_2, generic_resource_type_3):
    pb = ProductBlockTable(
        name="PB_2",
        description="Generic Product Block 2",
        tag="PB2",
        status="active",
        resource_types=[generic_resource_type_2, generic_resource_type_3],
        created_at=datetime.datetime.fromisoformat("2023-05-24T00:00:00+00:00"),
    )
    db.session.add(pb)
    db.session.commit()
    return pb


@pytest.fixture
def generic_product_block_3(generic_resource_type_2):
    pb = ProductBlockTable(
        name="PB_3",
        description="Generic Product Block 3",
        tag="PB3",
        status="active",
        resource_types=[generic_resource_type_2],
        created_at=datetime.datetime.fromisoformat("2023-05-24T00:00:00+00:00"),
    )
    db.session.add(pb)
    db.session.commit()
    return pb


@pytest.fixture
def generic_product_1(generic_product_block_1, generic_product_block_2):
    workflow = db.session.scalar(select(WorkflowTable).where(WorkflowTable.name == "modify_note"))
    p = ProductTable(
        name="Product 1",
        description="Generic Product One",
        product_type="Generic",
        status="active",
        tag="GEN1",
        product_blocks=[generic_product_block_1, generic_product_block_2],
        workflows=[workflow],
    )
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def generic_product_2(generic_product_block_3):
    workflow = db.session.scalar(select(WorkflowTable).where(WorkflowTable.name == "modify_note"))

    p = ProductTable(
        name="Product 2",
        description="Generic Product Two",
        product_type="Generic",
        status="active",
        tag="GEN2",
        product_blocks=[generic_product_block_3],
        workflows=[workflow],
    )
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def generic_product_3(generic_product_block_2):
    p = ProductTable(
        name="Product 3",
        description="Generic Product Three",
        product_type="Generic",
        status="active",
        tag="GEN3",
        product_blocks=[generic_product_block_2],
    )
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def generic_product_block_type_1(generic_product_block_1):
    class GenericProductBlockOneInactive(ProductBlockModel, product_block_name="PB_1"):
        rt_1: str | None = None

    class GenericProductBlockOne(GenericProductBlockOneInactive, lifecycle=[SubscriptionLifecycle.ACTIVE]):
        rt_1: str

    return GenericProductBlockOneInactive, GenericProductBlockOne


@pytest.fixture
def generic_product_block_type_2(generic_product_block_2):
    class GenericProductBlockTwoInactive(ProductBlockModel, product_block_name="PB_2"):
        rt_2: int | None = None
        rt_3: str | None = None

    class GenericProductBlockTwo(GenericProductBlockTwoInactive, lifecycle=[SubscriptionLifecycle.ACTIVE]):
        rt_2: int
        rt_3: str

    return GenericProductBlockTwoInactive, GenericProductBlockTwo


@pytest.fixture
def generic_product_block_type_3(generic_product_block_3):
    class GenericProductBlockThreeInactive(ProductBlockModel, product_block_name="PB_3"):
        rt_2: int | None = None

    class GenericProductBlockThree(GenericProductBlockThreeInactive, lifecycle=[SubscriptionLifecycle.ACTIVE]):
        rt_2: int

    return GenericProductBlockThreeInactive, GenericProductBlockThree


@pytest.fixture
def generic_product_type_1(generic_product_1, generic_product_block_type_1, generic_product_block_type_2):
    generic_product_block_one_inactive, generic_product_block_one = generic_product_block_type_1
    generic_product_block_two_inactive, generic_product_block_two = generic_product_block_type_2

    # Test Product domain models

    class GenericProductOneInactive(SubscriptionModel, is_base=True):
        pb_1: generic_product_block_one_inactive
        pb_2: generic_product_block_two_inactive

    class GenericProductOne(GenericProductOneInactive, lifecycle=[SubscriptionLifecycle.ACTIVE]):
        pb_1: generic_product_block_one
        pb_2: generic_product_block_two

    SUBSCRIPTION_MODEL_REGISTRY["Product 1"] = GenericProductOne

    yield GenericProductOneInactive, GenericProductOne

    del SUBSCRIPTION_MODEL_REGISTRY["Product 1"]


@pytest.fixture
def generic_product_type_2(generic_product_2, generic_product_block_type_3):
    generic_product_block_three_inactive, generic_product_block_three = generic_product_block_type_3

    class GenericProductTwoInactive(SubscriptionModel, is_base=True):
        pb_3: generic_product_block_three_inactive

    class GenericProductTwo(GenericProductTwoInactive, lifecycle=[SubscriptionLifecycle.ACTIVE]):
        pb_3: generic_product_block_three

    SUBSCRIPTION_MODEL_REGISTRY["Product 2"] = GenericProductTwo

    yield GenericProductTwoInactive, GenericProductTwo

    del SUBSCRIPTION_MODEL_REGISTRY["Product 2"]


@pytest.fixture
def product_type_1_subscription_factory(generic_product_1, generic_product_type_1, geant_partner):
    def subscription_create(
        description="Generic Subscription One",
        start_date=DEFAULT_START_DATE,
        rt_1="Value1",
        rt_2=42,
        rt_3="Value2",
    ):
        generic_product_one_inactive, _ = generic_product_type_1
        gen_subscription = generic_product_one_inactive.from_product_id(
            generic_product_1.product_id, customer_id=geant_partner["partner_id"], insync=True
        )
        gen_subscription.pb_1.rt_1 = rt_1
        gen_subscription.pb_2.rt_2 = rt_2
        gen_subscription.pb_2.rt_3 = rt_3
        gen_subscription = SubscriptionModel.from_other_lifecycle(gen_subscription, SubscriptionLifecycle.ACTIVE)
        gen_subscription.description = description
        gen_subscription.start_date = start_date
        gen_subscription.save()

        gen_subscription_metadata = SubscriptionMetadataTable()
        gen_subscription_metadata.subscription_id = gen_subscription.subscription_id
        gen_subscription_metadata.metadata_ = {"description": "Some metadata description"}
        db.session.add(gen_subscription_metadata)
        db.session.commit()
        return str(gen_subscription.subscription_id)

    return subscription_create


@pytest.fixture
def product_type_1_subscriptions_factory(product_type_1_subscription_factory):
    def subscriptions_create(amount=1):
        return [
            product_type_1_subscription_factory(
                description=f"Subscription {i}",
                start_date=(
                    datetime.datetime.fromisoformat("2023-05-24T00:00:00+00:00") + datetime.timedelta(days=i)
                ).replace(tzinfo=datetime.UTC),
            )
            for i in range(amount)
        ]

    return subscriptions_create


@pytest.fixture
def generic_subscription_1(product_type_1_subscription_factory):
    return product_type_1_subscription_factory()


@pytest.fixture(scope="session", autouse=True)
def responses():
    """Prevent unit test cases from sending HTTP requests."""
    responses_mock = Responses("requests.packages.urllib3")

    def _find_request(call):
        mock_url = responses_mock._find_match(call.request)  # noqa: SLF001
        if not mock_url:
            pytest.fail(f"Call not mocked: {call.request}")
        return mock_url

    with responses_mock:
        yield responses_mock

        mocked_urls = map(itemgetter("url", "method", "match_querystring"), responses_mock._urls)  # noqa: SLF001
        used_urls = map(itemgetter("url", "method", "match_querystring"), map(_find_request, responses_mock.calls))
        not_used = set(mocked_urls) - set(used_urls)
        if not_used:
            pytest.fail(f"Found unused responses mocks: {not_used}", pytrace=False)
