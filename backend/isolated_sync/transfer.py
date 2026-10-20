"""T6.6C §15.3 typed, observation-rooted transfer. Not a hash download API.

Only the explicitly constructed isolated HTTP app calls this module. No schema,
financial writes, pin release, graph enumeration, network streaming or GC here.
Response chunks are bounded; validation work also depends on the complete size
of each requested immutable object (including an oversized singleton).
"""

import base64
from collections import OrderedDict
from dataclasses import dataclass
import sqlite3
from time import perf_counter

from app.authoritative_schemas import AuthoritativeProjections
from isolated_sync.canonical import CanonicalError, Context, HASH, Key, Namespace, encode
from isolated_sync.observation import ObservationError, reject, uuid
from isolated_sync.patricia import Fact, bits
from isolated_sync.raw import PRIMARY, SHAPES, TABLES, Row
from isolated_sync.roots import u64
from isolated_sync.segments import FANOUT, MIN_FANOUT, leaf
from isolated_sync.store import Store


MIB = 1048576


def natural(value):
    return int(u64(value))


@dataclass(frozen=True)
class TransferLimits:
    request_bytes: int = 3 * MIB  # All 64 legal 512-hash paths fit.
    batch_items: int = 64
    batch_decoded_bytes: int = MIB
    chunk_bytes: int = MIB
    path_depth: int = 512
    concurrent_requests: int = 2
    body_seconds: int = 10

    def __post_init__(self):
        for name, maximum in (("batch_items", 64), ("batch_decoded_bytes", MIB),
                              ("chunk_bytes", MIB), ("path_depth", 512), ("concurrent_requests", 16)):
            if type(getattr(self, name)) is not int or not 1 <= getattr(self, name) <= maximum:
                reject("INVALID_LIMITS")
        if type(self.request_bytes) is not int or not 1024 <= self.request_bytes <= 3 * MIB:
            reject("INVALID_LIMITS")
        if type(self.body_seconds) is not int or not 1 <= self.body_seconds <= 60:
            reject("INVALID_LIMITS")


def fields(value, names):
    if type(value) is not dict or set(value) != set(names):
        reject("INVALID_REQUEST")


def object_request(value, limits):
    fields(value, ("protocol", "request_id", "items"))
    uuid(value["request_id"])
    if type(value["protocol"]) is not int or value["protocol"] != 1:
        reject("UNSUPPORTED_CONTRACT")
    items = value["items"]
    if type(items) is not list or not items:
        reject("INVALID_REQUEST")
    if len(items) > limits.batch_items:
        reject("TRANSFER_BUDGET", "retry_same")
    total = 0
    for item in items:
        fields(item, ("path", "offset", "length"))
        path = item["path"]
        if type(path) is not list or not path:
            reject("INVALID_REQUEST")
        if len(path) > limits.path_depth:
            reject("TRANSFER_BUDGET", "retry_same")
        if any(type(h) is not str or not HASH.fullmatch(h) for h in path) or len(set(path)) != len(path):
            reject("INVALID_REQUEST")
        u64(item["offset"])
        length = item["length"]
        if type(length) is not int or length < 1:
            reject("INVALID_REQUEST")
        total += length  # Python integers cannot overflow.
        if length > limits.chunk_bytes or total > limits.batch_decoded_bytes:
            reject("TRANSFER_BUDGET", "retry_same")
    return value


def reference(ref):
    fields(ref, ("hash", "bytes"))
    if type(ref["hash"]) is not str or not HASH.fullmatch(ref["hash"]) or not natural(ref["bytes"]):
        reject("REQUIRED_METADATA_INVALID")


def descriptor(value, table):
    fields(value, ("ref", "height", "count", "min", "max"))
    reference(value["ref"])
    height, count = value["height"], natural(value["count"])
    if type(height) is not int or not 0 <= height <= 63:
        reject("REQUIRED_METADATA_INVALID")
    if not count:
        if height or value["min"] is not None or value["max"] is not None:
            reject("REQUIRED_METADATA_INVALID")
    else:
        low, high = Key.parse(value["min"]), Key.parse(value["max"])
        if (low.order() > high.order() or any((type(k.value) is int) != (PRIMARY[table] == "id") for k in (low, high))):
            reject("REQUIRED_METADATA_INVALID")


@dataclass(frozen=True)
class Edge:
    ref: dict
    kinds: frozenset
    table: str | None = None
    desc: dict | None = None
    root: bool = False
    prefix: str = ""
    count: int | None = None
    parent_count: int | None = None


class PathResolver:
    """No client-supplied parent is trusted; each edge comes from verified bytes.

    Zero object cache bounds payload retention to the current object. Optional
    verified PREFIX metadata is private to one acquire/transaction, never a
    terminal-object, authorization, or cross-request cache.
    Empty/row/fact hash strings are never interpreted as graph edges.
    """

    def __init__(self, conn, repo, target, check_cancelled=None, *, prefix_capacity=0, prefix_bytes=0):
        self.conn, self.repo, self.target = conn, repo, target
        self.check_cancelled = check_cancelled
        self.context = Context(Namespace(**target["ns"]), target["versions"]["raw_schema"])
        self.store = Store(conn, self.context, capacity=0)
        self.reads = self.bytes_read = 0
        if not 0 <= prefix_capacity <= 64*512 or not 0 <= prefix_bytes <= MIB:
            reject("INVALID_LIMITS")
        self._prefix_capacity, self._prefix_budget = prefix_capacity, prefix_bytes
        self._prefixes = OrderedDict()
        self._prefix_size = 0
        self._transaction_changes = conn.total_changes
        self.prefix_hits = self.prefix_misses = self.prefix_peak = self.prefix_byte_peak = 0

    def clear_prefixes(self):
        self._prefixes.clear()
        self._prefix_size = 0

    def _prefix_key(self, path, position, edge):
        # Component identity, never textual startswith or hash-only reuse. The
        # request owns a fixed Target/NS/Versions and a private locked connection.
        d = edge.desc
        desc = None if d is None else (d["height"], d["count"],
                None if d["min"] is None else tuple(d["min"]),
                None if d["max"] is None else tuple(d["max"]))
        return (tuple(path[:position+1]), edge.ref["hash"], edge.ref["bytes"],
                edge.kinds, edge.table, desc, edge.root, edge.prefix, edge.count, edge.parent_count)

    def _remember_prefix(self, key, children, size):
        if not self._prefix_capacity or size > self._prefix_budget:
            return  # Oversized metadata follows the original strict path.
        while self._prefixes and (len(self._prefixes) >= self._prefix_capacity or
                                  self._prefix_size+size > self._prefix_budget):
            _, (_, charge) = self._prefixes.popitem(last=False)
            self._prefix_size -= charge
        self._prefixes[key] = (children, size)
        self._prefix_size += size
        self.prefix_peak = max(self.prefix_peak, len(self._prefixes))
        self.prefix_byte_peak = max(self.prefix_byte_peak, self._prefix_size)

    def resolve(self, path):
        roots = {self.target[role+"_ref"]["hash"]: Edge(self.target[role+"_ref"], frozenset({kind}), root=True)
                 for role, kind in (("raw", "raw-root"), ("index", "index-root"), ("hot", "hot"), ("control", "control"))}
        edge = roots.get(path[0])
        if edge is None:
            reject("INVALID_REQUEST")  # Do not query an arbitrary guessed hash.
        for position, digest in enumerate(path):
            if self.check_cancelled:
                self.check_cancelled()
            if digest != edge.ref["hash"]:
                reject("INVALID_REQUEST")
            terminal = position == len(path)-1
            key = None
            if self._prefix_capacity:
                # acquire is synchronous under the original BEGIN IMMEDIATE;
                # no await or foreign writer can intervene. Do not reuse after
                # an unexpected transaction loss or local write either.
                if not self.conn.in_transaction or self.conn.total_changes != self._transaction_changes:
                    self.clear_prefixes()
                    reject("REQUIRED_METADATA_INVALID")
                if not terminal:
                    key = self._prefix_key(path, position, edge)
                    cached = self._prefixes.get(key)
                    if cached is not None:
                        self._prefixes.move_to_end(key)
                        self.prefix_hits += 1
                        edge = cached[0].get(path[position+1])
                        if edge is None:
                            reject("INVALID_REQUEST")
                        continue
                    self.prefix_misses += 1
            self.reads += 1
            try:
                if edge.kinds <= {"hot", "control"}:
                    obj = self.repo._view_object(self.conn, edge.ref, next(iter(edge.kinds)), self.target["ns"])
                else:
                    obj = self.store.get(edge.ref, edge.kinds)
            except CanonicalError as error:
                if str(error) == "REJECT_OBJECT_MISSING":
                    reject("OBSERVATION_INCOMPLETE", "new_observation")
                raise
            self.bytes_read += len(obj.raw)
            try:
                children = self.validate(obj, edge)
            except ObservationError as error:
                if error.code == "INVALID_REQUEST":
                    reject("REQUIRED_METADATA_INVALID")
                raise
            if terminal:
                return obj
            if key is not None:
                self._remember_prefix(key, children, len(obj.raw))
            edge = children.get(path[position+1])
            if edge is None:
                reject("INVALID_REQUEST")  # No lookup of the forged child.
        reject("INVALID_REQUEST")

    def validate(self, obj, edge):
        """Local shapes/context/descriptor checks, NOT an O(N) authority rebuild.

        Complete-state authority is the D2b certificate checked by D3a. This
        validates every visited object and typed edge independently of the
        auxiliary sync_object_edges table. Global checks remain client gates.
        """
        body, kind = obj.body(), obj.kind
        common = set(self.context.fields()) | {"kind"}
        result = {}

        def add(child):
            reference(child.ref)
            if child.ref["hash"] in result:
                reject("REQUIRED_METADATA_INVALID")
            result[child.ref["hash"]] = child

        if kind == "raw-root":
            fields(body, common | {"tables"})
            if type(body["tables"]) is not list or len(body["tables"]) != len(TABLES):
                reject("REQUIRED_METADATA_INVALID")
            for table, entry in zip(TABLES, body["tables"]):
                fields(entry, ("name", "root", "count"))
                if entry["name"] != table or entry["count"] != entry["root"]["count"]:
                    reject("REQUIRED_METADATA_INVALID")
                descriptor(entry["root"], table)
                d = entry["root"]
                add(Edge(d["ref"], frozenset({"snapshot-node" if d["height"] else "snapshot-leaf"}), table, d, True))
        elif kind in {"snapshot-leaf", "snapshot-node"}:
            names = common | {"table", "height", "count", "min", "max"}
            fields(body, names | ({"oversized", "rows"} if kind == "snapshot-leaf" else {"children"}))
            if type(body["height"]) is not int or body["table"] != edge.table or encode({k: body[k] for k in ("height", "count", "min", "max")}) != encode({k: edge.desc[k] for k in ("height", "count", "min", "max")}):
                reject("REQUIRED_METADATA_INVALID")
            if kind == "snapshot-leaf":
                if type(body["rows"]) is not list or type(body["oversized"]) is not bool or (not edge.root and not body["rows"]):
                    reject("REQUIRED_METADATA_INVALID")
                rows = []
                for item in body["rows"]:
                    fields(item, ("key", "value"))
                    row = Row.make(edge.table, item["value"])
                    if row.key.wire() != item["key"] or (rows and rows[-1].key.order() >= row.key.order()):
                        reject("REQUIRED_METADATA_INVALID")
                    rows.append(row)
                if leaf(self.context, edge.table, rows).object.raw != obj.raw:
                    reject("REQUIRED_METADATA_INVALID")
            else:
                children = body["children"]
                if type(children) is not list or not (2 if edge.root else MIN_FANOUT) <= len(children) <= FANOUT:
                    reject("REQUIRED_METADATA_INVALID")
                previous, total = None, 0
                for d in children:
                    descriptor(d, edge.table)
                    if not natural(d["count"]) or d["height"]+1 != body["height"] or (previous is not None and Key.parse(previous).order() >= Key.parse(d["min"]).order()):
                        reject("REQUIRED_METADATA_INVALID")
                    total += natural(d["count"])
                    previous = d["max"]
                    add(Edge(d["ref"], frozenset({"snapshot-node" if d["height"] else "snapshot-leaf"}), edge.table, d))
                if str(total) != body["count"] or children[0]["min"] != body["min"] or children[-1]["max"] != body["max"]:
                    reject("REQUIRED_METADATA_INVALID")
        elif kind.startswith("index-"):
            if type(body.get("structural")) is not int or body["structural"] != 1:
                reject("REQUIRED_METADATA_INVALID")
            count = natural(body["count"])
            if (edge.count is not None and count != edge.count) or (edge.parent_count is not None and not 0 < count < edge.parent_count):
                reject("REQUIRED_METADATA_INVALID")
            names = common | {"structural", "count"}
            if kind == "index-root":
                fields(body, names | {"facts"})
                add(Edge(body["facts"], frozenset({"index-empty"} if count == 0 else {"index-node", "index-leaf"}), count=count))
            elif kind == "index-empty":
                fields(body, names)
                if count or edge.prefix:
                    reject("REQUIRED_METADATA_INVALID")
            elif kind == "index-leaf":
                fields(body, names | {"digest", "facts"})
                if type(body["digest"]) is not str or not HASH.fullmatch(body["digest"]) or not bits(body["digest"]).startswith(edge.prefix):
                    reject("REQUIRED_METADATA_INVALID")
                if type(body["facts"]) is not list or len(body["facts"]) != count or not count:
                    reject("REQUIRED_METADATA_INVALID")
                prior = None
                for value in body["facts"]:
                    fields(value, ("key", "value"))
                    fact = Fact.make(value["key"], value["value"])
                    if fact.digest != body["digest"] or (prior is not None and prior >= fact.key):
                        reject("REQUIRED_METADATA_INVALID")
                    prior = fact.key
            elif kind == "index-node":
                fields(body, names | {"prefix", "left", "right"})
                p = body["prefix"]
                if type(p) is not str or len(p) > 255 or set(p)-{"0", "1"} or not p.startswith(edge.prefix) or count < 2:
                    reject("REQUIRED_METADATA_INVALID")
                for bit, side in (("0", "left"), ("1", "right")):
                    add(Edge(body[side], frozenset({"index-node", "index-leaf"}), prefix=p+bit, parent_count=count))
        elif kind == "hot":
            fields(body, ("kind", "ns", "canon", "projection_schema", "context", "state"))
            if type(body["canon"]) is not int or body["canon"] != 1 or body["context"] != self.target["context"] or body["projection_schema"] != self.target["versions"]["projection_schema"]:
                reject("REQUIRED_METADATA_INVALID")
            if type(body["state"]) is not dict or set(body["state"]) != set(AuthoritativeProjections.model_fields):
                reject("REQUIRED_METADATA_INVALID")
        elif kind == "control":
            fields(body, ("kind", "ns", "canon", "snapshot_schema", "recurring_ownership_version", "exported_at", "range", "card_charge_policy", "columns", "discount_policy_defaults"))
            if (type(body["canon"]) is not int or body["canon"] != 1 or type(body["snapshot_schema"]) is not int or body["snapshot_schema"] != 7 or
                    type(body["recurring_ownership_version"]) is not int or body["recurring_ownership_version"] != 1 or body["range"] != {"scope": "all"} or
                    body["columns"] != {t: sorted(SHAPES[t]) for t in TABLES}):
                reject("REQUIRED_METADATA_INVALID")
        else:
            reject("INVALID_REQUEST")
        return result


class TransferRepository:
    def __init__(self, observation, *, limits=TransferLimits()):
        self.observation, self.limits = observation, limits

    def acquire(self, observation_id, credential, *, guard, request, fault=None, check_cancelled=None):
        """Prepare ALL response bytes, then terminal auth + expiry, then close DB.

        The short audited metadata scope preserves sticky retirement on errors.
        No transaction survives this call or an ASGI send/network await. Metrics
        are returned per call, so concurrent requests never share mutable state.
        """
        uuid(observation_id)
        object_request(request, self.limits)
        started = perf_counter()
        repo = self.observation
        try:
            with repo._connection() as (conn, retired):
                manifest = repo._lookup(conn, retired, observation_id, credential, guard)
                admitted = perf_counter()
                resolver = PathResolver(conn, repo, manifest["target"], check_cancelled,
                                        prefix_capacity=self.limits.batch_items*self.limits.path_depth,
                                        prefix_bytes=self.limits.batch_decoded_bytes)
                chunks = []
                try:
                    for item in request["items"]:
                        obj = resolver.resolve(item["path"])
                        offset, length = natural(item["offset"]), item["length"]
                        if offset+length > len(obj.raw):
                            reject("INVALID_REQUEST")
                        chunks.append(dict(ref=obj.ref(), offset=item["offset"], length=length,
                                           data_base64=base64.b64encode(obj.raw[offset:offset+length]).decode("ascii")))
                        del obj
                finally:
                    resolver.clear_prefixes()  # Before terminal guard/DB close, including errors/cancellation.
                resolved = perf_counter()
                if check_cancelled:
                    check_cancelled()
                payload = encode(dict(protocol=1, request_id=request["request_id"], observation_id=observation_id, chunks=chunks))
                # Fixed framing allowance plus exactly bounded base64 expansion.
                if len(payload) > 4*((self.limits.batch_decoded_bytes+2)//3)+self.limits.batch_items*256+512:
                    reject("TRANSFER_BUDGET", "retry_same")
                if fault:
                    fault("prepared", conn)
                row = conn.execute("SELECT * FROM sync_observations WHERE id=?", (observation_id,)).fetchone()
                terminal = repo._guard(conn, credential, guard)
                repo._check_lease(conn, retired, row, credential, terminal)
                finished = perf_counter()
            return payload, dict(admission_ms=(admitted-started)*1000, resolution_ms=(resolved-admitted)*1000,
                                 terminal_serialization_ms=(finished-resolved)*1000, total_ms=(perf_counter()-started)*1000,
                                 object_reads=resolver.reads, object_bytes_read=resolver.bytes_read, response_bytes=len(payload),
                                 prefix_cache_hits=resolver.prefix_hits, prefix_validations=resolver.prefix_misses,
                                 prefix_cache_peak=resolver.prefix_peak, prefix_cache_peak_bytes=resolver.prefix_byte_peak,
                                 decoded_bytes=sum(i["length"] for i in request["items"]), path_edges=sum(len(i["path"])-1 for i in request["items"]))
        except CanonicalError as error:
            if str(error) == "REJECT_OBJECT_MISSING":
                reject("OBSERVATION_INCOMPLETE", "new_observation")
            reject("REQUIRED_METADATA_INVALID")
        except sqlite3.OperationalError as error:
            if "locked" in str(error) or "busy" in str(error):
                reject("ROOT_NOT_READY", "retry_same")
            reject("STORAGE_FAILED")
        except (KeyError, TypeError, IndexError, OverflowError):
            reject("REQUIRED_METADATA_INVALID")
