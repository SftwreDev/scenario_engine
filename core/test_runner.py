from django.test.runner import DiscoverRunner


class ForceDestroyPostgresTestRunner(DiscoverRunner):
    """
    A custom test runner that uses PostgreSQL 13's `WITH (FORCE)` clause
    to ensure the test database drops cleanly despite active pooler sessions.
    """

    def __init__(self, *args, **kwargs):
        # Force non-interactive database destruction on setup if it exists
        kwargs["interactive"] = False
        super().__init__(*args, **kwargs)

    def setup_databases(self, **kwargs):
        from django.db import connections

        for alias in connections:
            connection = connections[alias]
            if connection.vendor == "postgresql":
                test_database_name = connection.creation._get_test_db_name()
                try:
                    with connection._nodb_cursor() as cursor:
                        print(
                            f"\\n[CustomTestRunner] Pre-emptively dropping {test_database_name}..."
                        )
                        cursor.execute(
                            f'DROP DATABASE IF EXISTS "{test_database_name}" WITH (FORCE);'
                        )
                except Exception as e:
                    print(
                        f"\\n[CustomTestRunner] Warning: Pre-emptive drop failed for {test_database_name}: {e}"
                    )
        return super().setup_databases(**kwargs)

    def teardown_databases(self, old_config, **kwargs):
        # We manually forcefully drop the postgres databases,
        # then tell Django NOT to drop them again.
        for connection, old_name, destroy in old_config:
            if destroy and connection.vendor == "postgresql":
                test_database_name = connection.creation._get_test_db_name()
                try:
                    with connection._nodb_cursor() as cursor:
                        print(
                            f"\\n[CustomTestRunner] Forcibly dropping {test_database_name}..."
                        )
                        cursor.execute(
                            f'DROP DATABASE IF EXISTS "{test_database_name}" WITH (FORCE);'
                        )
                except Exception as e:
                    print(
                        f"\\n[CustomTestRunner] Warning: Force drop failed for {test_database_name}: {e}"
                    )

        # Update config so Django's default teardown skips the DROP step
        new_config = []
        for connection, old_name, destroy in old_config:
            if connection.vendor == "postgresql":
                new_config.append((connection, old_name, False))
            else:
                new_config.append((connection, old_name, destroy))

        super().teardown_databases(new_config, **kwargs)
