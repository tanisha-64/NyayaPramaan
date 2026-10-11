"""
Tiny in-memory stand-in for the parts of supabase-py the app uses. Unlike MagicMock chains it actually applies
filters, so authorization and isolation tests fail when the code forgets a filter instead of passing by accident.
"""
import copy
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table
        self._filters = []
        self._op = "select"
        self._payload = None
        self._count = None
        self._limit = None
        self._range = None
        self._order = None

    def select(self, cols="*", count=None):
        self._op = "select"
        self._count = count
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col, val):
        self._filters.append(lambda r, c=col, v=val: str(r.get(c)) == str(v))
        return self

    def in_(self, col, vals):
        vals = {str(v) for v in vals}
        self._filters.append(lambda r, c=col, v=vals: str(r.get(c)) in v)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, a, b):
        self._range = (a, b)
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def execute(self):
        self.client.calls.append((f"{self.table_name}.{self._op}", copy.deepcopy(self._payload)))
        failure = self.client.fail_on.get((self.table_name, self._op))
        if failure and failure(self._payload):
            raise RuntimeError(f"injected failure on {self.table_name}.{self._op}")
        rows = self.client.tables.setdefault(self.table_name, [])
        matches = [r for r in rows if all(f(r) for f in self._filters)]
        if self._op == "insert":
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            out = []
            for item in items:
                row = copy.deepcopy(item)
                row.setdefault("id", str(uuid.uuid4()))
                self.client._clock += 1
                row.setdefault("created_at", (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=self.client._clock)).isoformat())
                rows.append(row)
                out.append(copy.deepcopy(row))
            return SimpleNamespace(data=out, count=None)
        if self._op == "update":
            for r in matches:
                r.update(copy.deepcopy(self._payload))
            return SimpleNamespace(data=copy.deepcopy(matches), count=None)
        if self._op == "delete":
            for r in matches:
                rows.remove(r)
            return SimpleNamespace(data=copy.deepcopy(matches), count=None)
        if self._order:
            col, desc = self._order
            matches = sorted(matches, key=lambda r: str(r.get(col)), reverse=desc)
        total = len(matches)
        if self._range:
            matches = matches[self._range[0]:self._range[1] + 1]
        if self._limit is not None:
            matches = matches[:self._limit]
        return SimpleNamespace(data=copy.deepcopy(matches), count=total if self._count else None)


class FakeRpc:
    def __init__(self, client, name, params):
        self.client = client
        self.name = name
        self.params = params

    def execute(self):
        self.client.calls.append((f"rpc:{self.name}", "call"))
        handler = self.client.rpc_handlers.get(self.name)
        if handler is None:
            raise RuntimeError(f"function {self.name} does not exist")
        return SimpleNamespace(data=handler(self.params), count=None)


class FakeSupabase:
    def __init__(self, tables=None, rpc_handlers=None, fail_on=None):
        self.tables = {k: copy.deepcopy(v) for k, v in (tables or {}).items()}
        self.rpc_handlers = rpc_handlers or {}
        self.fail_on = fail_on or {}
        self.calls = []
        self._clock = 0

    def table(self, name):
        return FakeQuery(self, name)

    def rpc(self, name, params):
        return FakeRpc(self, name, params)

    def rows(self, table):
        return self.tables.get(table, [])

    def chunk_ids(self, case_id):
        return {r["id"] for r in self.rows("document_chunks") if r.get("case_id") == case_id}
