from __future__ import annotations

from contextlib import contextmanager

from django.db import connection, transaction


class LockKey:
    """
    Stable keys for advisory locks.

    Values are arbitrary but must never be reused for a different purpose,
    since every caller of the same key serializes against the others.
    """

    PAYOUT_RULE_ACTIVATION = 881_001


@contextmanager
def advisory_lock(key: int):
    """
    Serialize a critical section across connections for the current transaction.

    Uses ``pg_advisory_xact_lock``, which is released automatically when the
    surrounding transaction commits or rolls back — there is no unlock path to
    leak. Must be called inside ``transaction.atomic()``.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError(
            "advisory_lock() must be used inside transaction.atomic(); a "
            "transaction-scoped lock outside a transaction would release "
            "immediately and protect nothing."
        )
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [key])
    yield
