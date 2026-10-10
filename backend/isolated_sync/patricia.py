"""Canonical persistent Patricia facts index, T6.6C §11.

Immutable C1 fact keys are independent of B+tree placement. Updates traverse a
single compressed digest path, never rebuild the complete facts collection.
"""

from bisect import bisect_left
from dataclasses import dataclass

from isolated_sync.canonical import Context, MAX_I64, Object, decode_c1, encode, fail, hash_bytes


@dataclass(frozen=True)
class Fact:
    key: bytes
    value: bytes

    def __post_init__(self):
        if type(decode_c1(self.key)) is not list:
            fail("REJECT_FACT_KEY")
        decode_c1(self.value)

    @classmethod
    def make(cls, key, value):
        return cls(encode(key), encode(value))

    def wire(self):
        return dict(key=decode_c1(self.key), value=decode_c1(self.value))

    @property
    def digest(self):
        return hash_bytes("fact-key", self.key)


def bits(digest):
    return "".join(f"{byte:08b}" for byte in bytes.fromhex(digest))


def common(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return a[:i]
    return a[:min(len(a), len(b))]


@dataclass(frozen=True)
class IndexNode:
    object: Object
    count: int
    prefix: str
    facts: tuple[Fact, ...] = ()
    left: "IndexNode | None" = None
    right: "IndexNode | None" = None


def _fields(context):
    return dict(**context.fields(), structural=1)


def _empty(context):
    return IndexNode(Object.make(dict(kind="index-empty", **_fields(context), count="0")), 0, "")


def _leaf(context, digest, facts):
    ordered = tuple(sorted(facts, key=lambda f: f.key))
    if not ordered or len({f.key for f in ordered}) != len(ordered):
        fail("REJECT_FACT_DUPLICATE")
    return IndexNode(Object.make(dict(kind="index-leaf", **_fields(context), digest=digest,
                                     count=str(len(ordered)), facts=[f.wire() for f in ordered])),
                     len(ordered), bits(digest), facts=ordered)


def _branch(context, left, right):
    prefix = common(left.prefix, right.prefix)
    if (not left.count or not right.count or len(prefix) == 256 or
            left.prefix[len(prefix)] != "0" or right.prefix[len(prefix)] != "1"):
        fail("REJECT_INDEX_BRANCH")
    count = left.count + right.count
    return IndexNode(Object.make(dict(kind="index-node", **_fields(context), prefix=prefix,
                                     left=left.object.ref(), right=right.object.ref(), count=str(count))),
                     count, prefix, left=left, right=right)


@dataclass(frozen=True)
class Index:
    context: Context
    root: IndexNode

    @classmethod
    def build(cls, context, facts=()):
        buckets = {}
        keys = set()
        for fact in facts:
            if fact.key in keys:
                fail("REJECT_FACT_DUPLICATE")
            keys.add(fact.key)
            buckets.setdefault(fact.digest, []).append(fact)
        leaves = [_leaf(context, digest, values) for digest, values in sorted(buckets.items())]

        def build(items):
            if len(items) == 1:
                return items[0]
            prefix = common(items[0].prefix, items[-1].prefix)
            i = next(i for i, node in enumerate(items) if node.prefix[len(prefix)] == "1")
            return _branch(context, build(items[:i]), build(items[i:]))
        return cls(context, build(leaves) if leaves else _empty(context))

    def object(self):
        return Object.make(dict(kind="index-root", **_fields(self.context),
                                facts=self.root.object.ref(), count=str(self.root.count)))

    def lookup(self, key):
        raw = encode(key)
        path = bits(hash_bytes("fact-key", raw))
        node = self.root
        while node.count:
            if not path.startswith(node.prefix):
                return None
            if node.facts:
                i = bisect_left([f.key for f in node.facts], raw)
                return node.facts[i] if i < len(node.facts) and node.facts[i].key == raw else None
            node = node.right if path[len(node.prefix)] == "1" else node.left
        return None

    def put(self, fact, *, replace=False):
        path = bits(fact.digest)

        def change(node):
            if not node.count:
                if replace:
                    fail("REJECT_FACT_MISSING")
                return _leaf(self.context, fact.digest, [fact])
            prefix = common(node.prefix, path)
            if len(prefix) < len(node.prefix):
                if replace:
                    fail("REJECT_FACT_MISSING")
                new = _leaf(self.context, fact.digest, [fact])
                return (_branch(self.context, new, node) if path[len(prefix)] == "0" else
                        _branch(self.context, node, new))
            if node.facts:
                facts = list(node.facts)
                i = bisect_left([f.key for f in facts], fact.key)
                exists = i < len(facts) and facts[i].key == fact.key
                if exists != replace:
                    fail("REJECT_FACT_MISSING" if replace else "REJECT_FACT_DUPLICATE")
                if exists:
                    if facts[i] == fact:
                        return node
                    facts[i] = fact
                else:
                    facts.insert(i, fact)
                return _leaf(self.context, fact.digest, facts)
            if path[len(node.prefix)] == "0":
                return _branch(self.context, change(node.left), node.right)
            return _branch(self.context, node.left, change(node.right))
        return Index(self.context, change(self.root))

    def delete(self, key):
        raw = encode(key)
        path = bits(hash_bytes("fact-key", raw))

        def change(node):
            if not node.count or not path.startswith(node.prefix):
                fail("REJECT_FACT_MISSING")
            if node.facts:
                facts = [f for f in node.facts if f.key != raw]
                if len(facts) == len(node.facts):
                    fail("REJECT_FACT_MISSING")
                return _leaf(self.context, node.object.body()["digest"], facts) if facts else None
            if path[len(node.prefix)] == "0":
                left = change(node.left)
                return _branch(self.context, left, node.right) if left else node.right
            right = change(node.right)
            return _branch(self.context, node.left, right) if right else node.left
        return Index(self.context, change(self.root) or _empty(self.context))

    def facts(self):
        """Canonical digest-order traversal, collision buckets C1-key ordered."""
        def visit(node):
            if node.facts:
                yield from node.facts
            elif node.count:
                yield from visit(node.left)
                yield from visit(node.right)
        return visit(self.root)

    def objects(self):
        yield self.object()

        def visit(node):
            yield node.object
            if node.left:
                yield from visit(node.left)
                yield from visit(node.right)
        yield from visit(self.root)

    def validate(self):
        """Explicit O(F) full representation/coverage validation, not per put."""
        seen, keys = set(), set()

        def visit(node, ancestor=""):
            if (type(node.count) is not int or not 0 <= node.count <= MAX_I64 or
                    type(node.prefix) is not str or set(node.prefix) - {"0", "1"}):
                fail("REJECT_INDEX_METADATA")
            if node.object.hash in seen:
                fail("REJECT_INDEX_DUPLICATE_CHILD")
            seen.add(node.object.hash)
            if not node.count:
                if node != self.root or node != _empty(self.context):
                    fail("REJECT_INDEX_EMPTY")
                return []
            if not node.prefix.startswith(ancestor):
                fail("REJECT_INDEX_PREFIX")
            if node.facts:
                digest = node.facts[0].digest
                if any(f.digest != digest or f.key in keys for f in node.facts):
                    fail("REJECT_INDEX_BUCKET")
                keys.update(f.key for f in node.facts)
                if len(keys) < len(node.facts):
                    fail("REJECT_FACT_DUPLICATE")
                expected = _leaf(self.context, digest, node.facts)
                paths = [bits(digest)]
            else:
                if node.left is None or node.right is None or len(node.prefix) > 255:
                    fail("REJECT_INDEX_BRANCH")
                paths = visit(node.left, node.prefix + "0") + visit(node.right, node.prefix + "1")
                if common(min(paths), max(paths)) != node.prefix:
                    fail("REJECT_INDEX_PREFIX")
                expected = _branch(self.context, node.left, node.right)
            if expected != node:
                fail("REJECT_INDEX_METADATA")
            return paths
        visit(self.root)
        return len(keys)
