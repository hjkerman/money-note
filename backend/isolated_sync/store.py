"""D2b immutable SQLite objects and path-local D2a adapters. No runtime imports.

The caller owns a write transaction and trusted metadata authorization. A Ref is
not authorization. This module deliberately has no HTTP, lease or GC API.
"""

from collections import OrderedDict
from functools import cached_property

from isolated_sync.canonical import HASH, Key, Object, decode_c1, encode, fail, hash_bytes
from isolated_sync.patricia import Fact, Index, bits
from isolated_sync.raw import Row
from isolated_sync.segments import Tree, branch, leaf
from isolated_sync.roots import u64


def edges(obj):
    body = obj.body()
    if obj.kind == "snapshot-node":
        return [child["ref"] for child in body["children"]]
    if obj.kind == "raw-root":
        return [table["root"]["ref"] for table in body["tables"]]
    if obj.kind == "index-node":
        return [body["left"], body["right"]]
    if obj.kind == "index-root":
        return [body["facts"]]
    return []


class Store:
    """Hash-on-read, bounded LRU; metrics count actual object SQL, not cache hits."""

    def __init__(self, conn, context, *, capacity=256):
        self.conn, self.context, self.capacity = conn, context, capacity
        self.cache = OrderedDict()
        self.reads = self.writes = self.bytes_written = 0
        self.changed_leaves = self.changed_tree_nodes = self.changed_index_nodes = 0

    def _remember(self, obj):
        self.cache[obj.hash] = obj
        self.cache.move_to_end(obj.hash)
        while len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
        return obj

    def put(self, obj):
        """Children must already be persisted. Conflicting content is fatal."""
        if not self.conn.in_transaction:
            fail("REJECT_OBJECT_TRANSACTION")
        body = obj.body()
        if encode({k: body.get(k) for k in self.context.fields()}) != encode(self.context.fields()):
            fail("REJECT_OBJECT_CONTEXT")
        found = self.conn.execute("SELECT kind,body FROM sync_objects WHERE hash=?", (obj.hash,)).fetchone()
        if found is not None:
            if tuple(found) != (obj.kind, obj.raw):
                fail("REJECT_OBJECT_CONFLICT")
            return self._remember(obj)
        refs = edges(obj)
        for ref in refs:
            child = self.conn.execute("SELECT length(body) FROM sync_objects WHERE hash=?", (ref["hash"],)).fetchone()
            if child is None or str(child[0]) != ref["bytes"]:
                fail("REJECT_OBJECT_MISSING")
        self.conn.execute("INSERT INTO sync_objects VALUES (?,?,?)", (obj.hash, obj.kind, obj.raw))
        for ref in refs:
            self.conn.execute("INSERT INTO sync_object_edges VALUES (?,?)", (obj.hash, ref["hash"]))
        self.writes += 1
        self.bytes_written += len(obj.raw)
        return self._remember(obj)

    def get(self, ref, kinds):
        if type(ref) is not dict or set(ref) != {"hash", "bytes"}:
            fail("REJECT_OBJECT_REF")
        if type(ref["hash"]) is not str or not HASH.fullmatch(ref["hash"]):
            fail("REJECT_OBJECT_REF")
        u64(ref["bytes"])
        if ref["hash"] in self.cache:
            obj = self.cache[ref["hash"]]
            self.cache.move_to_end(obj.hash)
        else:
            self.reads += 1
            record = self.conn.execute("SELECT kind,body FROM sync_objects WHERE hash=?", (ref["hash"],)).fetchone()
            if record is None:
                fail("REJECT_OBJECT_MISSING")
            obj = Object(record["kind"], record["body"])
            self._remember(obj)
        if obj.ref() != ref or obj.kind not in kinds:
            fail("REJECT_OBJECT_IDENTITY")
        body = obj.body()
        if encode({k: body.get(k) for k in self.context.fields()}) != encode(self.context.fields()):
            fail("REJECT_OBJECT_CONTEXT")
        return obj

    def tree(self, table, descriptor):
        return Tree(self.context, table, LazyTree(self, table, descriptor))

    def index(self, ref):
        obj = self.get(ref, {"index-root"})
        body = obj.body()
        if (set(body) != set(self.context.fields()) | {"kind", "structural", "facts", "count"} or
                type(body["structural"]) is not int or body["structural"] != 1):
            fail("REJECT_STRUCTURAL_VERSION")
        u64(body["count"])
        root = LazyIndex(self, body["facts"])
        if str(root.count) != body["count"]:
            fail("REJECT_INDEX_COUNT")
        return Index(self.context, root)

    def persist_tree(self, node):
        """Visit NEW paths only; accepted immutable subtrees are opaque references."""
        if isinstance(node, LazyTree):
            return
        self.changed_leaves += node.height == 0
        self.changed_tree_nodes += node.height > 0
        for child in node.children:
            self.persist_tree(child)
        self.put(node.object)

    def persist_index(self, node):
        if isinstance(node, LazyIndex):
            return
        self.changed_index_nodes += 1
        if node.left:
            self.persist_index(node.left)
            self.persist_index(node.right)
        self.put(node.object)


class LazyObject:
    """A reference can be serialized without reading its immutable payload."""
    def __init__(self, store, ref, kinds):
        self.store, self.reference, self.kinds = store, ref, kinds
        self.hash = ref["hash"]

    def ref(self):
        return self.reference.copy()

    @cached_property
    def resolved(self):
        return self.store.get(self.reference, self.kinds)

    @property
    def raw(self):
        return self.resolved.raw

    @property
    def kind(self):
        return self.resolved.kind

    def body(self):
        return self.resolved.body()


class LazyTree:
    def __init__(self, store, table, descriptor):
        if (set(descriptor) != {"ref", "height", "count", "min", "max"} or
                type(descriptor["height"]) is not int or not 0 <= descriptor["height"] <= 63):
            fail("REJECT_TREE_DESCRIPTOR")
        u64(descriptor["count"])
        self.store, self.table, self.desc = store, table, descriptor
        self.height, self.count = descriptor["height"], int(descriptor["count"])
        self.minimum = Key.parse(descriptor["min"]) if descriptor["min"] is not None else None
        self.maximum = Key.parse(descriptor["max"]) if descriptor["max"] is not None else None

    def descriptor(self):
        return self.desc.copy()

    @cached_property
    def object(self):
        return LazyObject(self.store, self.desc["ref"], {"snapshot-leaf", "snapshot-node"})

    @cached_property
    def loaded(self):
        body = self.object.body()
        if body.get("table") != self.table:
            fail("REJECT_TREE_TABLE")
        if body["kind"] == "snapshot-leaf":
            node = leaf(self.store.context, self.table, [Row.make(self.table, r["value"]) for r in body["rows"]])
        else:
            children = tuple(LazyTree(self.store, self.table, d) for d in body["children"])
            if any(a.maximum.order() >= b.minimum.order() for a, b in zip(children, children[1:])):
                fail("REJECT_TREE_RANGE")
            node = branch(self.store.context, self.table, children)
        if node.object.raw != self.object.raw or encode(node.descriptor()) != encode(self.desc):
            fail("REJECT_TREE_DESCRIPTOR")
        return node

    @property
    def children(self):
        return self.loaded.children

    @property
    def rows(self):
        return self.loaded.rows


class LazyIndex:
    def __init__(self, store, ref):
        self.store, self.ref = store, ref

    @cached_property
    def object(self):
        return LazyObject(self.store, self.ref, {"index-empty", "index-leaf", "index-node"})

    @cached_property
    def body(self):
        body = self.object.body()
        if type(body.get("structural")) is not int or body["structural"] != 1:
            fail("REJECT_STRUCTURAL_VERSION")
        u64(body["count"])
        if self.object.kind == "index-node" and (type(body.get("prefix")) is not str or
                set(body["prefix"]) - {"0", "1"} or len(body["prefix"]) > 255):
            fail("REJECT_INDEX_PREFIX")
        return body

    @property
    def count(self):
        return int(self.body["count"])

    @property
    def prefix(self):
        return bits(self.body["digest"]) if self.object.kind == "index-leaf" else self.body.get("prefix", "")

    @cached_property
    def facts(self):
        return tuple(Fact.make(f["key"], f["value"]) for f in self.body.get("facts", []))

    @cached_property
    def left(self):
        return LazyIndex(self.store, self.body["left"]) if "left" in self.body else None

    @cached_property
    def right(self):
        return LazyIndex(self.store, self.body["right"]) if "right" in self.body else None


def row_object(context, row):
    """§11 row preimage is NOT a kind-bearing transferable Object body."""
    raw = encode(dict(ns=context.ns.wire(), raw_schema=context.raw_schema, table=row.table,
                      key=row.key.wire(), value=row.value()))
    return hash_bytes("row", raw), raw


def verify_row_object(context, digest, raw):
    body = decode_c1(raw)
    row = Row.make(body["table"], body["value"])
    if row_object(context, row) != (digest, raw):
        fail("REJECT_ROW_OBJECT")
    return row
