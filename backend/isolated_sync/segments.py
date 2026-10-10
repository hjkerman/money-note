"""Persistent PK B+tree, T6.6C §8 profile. No store, transactions or compaction.

Mutations copy only affected leaves/paths. Full validation is an explicit test /
bootstrap operation, never an implicit step in each update. Old versions survive.
"""

from bisect import bisect_left
from dataclasses import dataclass

from isolated_sync.canonical import Context, Key, MAX_I64, Object, encode, fail
from isolated_sync.raw import PRIMARY, TABLES, Row


LEAF_ROWS, LEAF_BYTES, FANOUT, MIN_FANOUT = 256, 262144, 32, 16


@dataclass(frozen=True)
class Node:
    object: Object
    height: int
    count: int
    minimum: Key | None
    maximum: Key | None
    rows: tuple[Row, ...] = ()
    children: tuple["Node", ...] = ()

    def descriptor(self):
        return dict(ref=self.object.ref(), height=self.height, count=str(self.count),
                    min=self.minimum.wire() if self.minimum else None,
                    max=self.maximum.wire() if self.maximum else None)


def _leaf_header(context, table, rows, oversized=False):
    return dict(kind="snapshot-leaf", **context.fields(), table=table, height=0,
                count=str(len(rows)), min=rows[0].key.wire() if rows else None,
                max=rows[-1].key.wire() if rows else None, oversized=oversized, rows=[])


def _row_bytes(row):
    return b'{"key":' + encode(row.key.wire()) + b',"value":' + row.raw + b'}'


def _leaf_size(context, table, rows, row_bytes):
    return len(encode(_leaf_header(context, table, rows))) + row_bytes + max(0, len(rows)-1)


def leaf(context, table, rows):
    rows = tuple(rows)
    raw_rows = b",".join(_row_bytes(row) for row in rows)
    ordinary = _leaf_size(context, table, rows, len(raw_rows) - max(0, len(rows)-1))
    oversized = len(rows) == 1 and ordinary > LEAF_BYTES
    if len(rows) > LEAF_ROWS or (ordinary > LEAF_BYTES and not oversized):
        fail("REJECT_LEAF_BOUNDS")
    body = _leaf_header(context, table, rows, oversized)
    # Use already admitted row bytes, preserving every token/storage distinction.
    raw = b"{" + b",".join(encode(k) + b":" + (b"[" + raw_rows + b"]" if k == "rows"
                          else encode(body[k])) for k in sorted(body)) + b"}"
    return Node(Object("snapshot-leaf", raw), 0, len(rows),
                rows[0].key if rows else None, rows[-1].key if rows else None, rows=rows)


def branch(context, table, children):
    children = tuple(children)
    if not children or len(children) > FANOUT or any(c.count == 0 for c in children):
        fail("REJECT_NODE_BOUNDS")
    height = children[0].height + 1
    if height > 63 or any(c.height != height-1 for c in children):
        fail("REJECT_HEIGHT")
    count = sum(c.count for c in children)
    body = dict(kind="snapshot-node", **context.fields(), table=table, height=height,
                count=str(count), min=children[0].minimum.wire(), max=children[-1].maximum.wire(),
                children=[c.descriptor() for c in children])
    return Node(Object.make(body), height, count, children[0].minimum, children[-1].maximum,
                children=children)


def _groups(values):
    groups = [values[i:i+FANOUT] for i in range(0, len(values), FANOUT)]
    if len(groups) > 1 and len(groups[-1]) < MIN_FANOUT:
        tail = groups[-2] + groups[-1]
        middle = len(tail)//2  # odd surplus on RIGHT
        groups[-2:] = [tail[:middle], tail[middle:]]
    return groups


@dataclass(frozen=True)
class Tree:
    context: Context
    table: str
    root: Node

    @classmethod
    def build(cls, context, table, rows=()):
        if table not in TABLES:
            fail("REJECT_TABLE")
        admitted = list(rows)
        for row in admitted:
            _check_row(table, row)
        ordered = sorted(admitted, key=lambda r: r.key.order())
        previous = None
        leaves, pending, size = [], [], 0
        for row in ordered:
            _check_row(table, row)
            if previous is not None and row.key.order() <= previous:
                fail("REJECT_DUPLICATE_PK")
            previous = row.key.order()
            encoded_size = len(_row_bytes(row))
            if pending and (len(pending) == LEAF_ROWS or
                            _leaf_size(context, table, pending + [row], size + encoded_size) > LEAF_BYTES):
                leaves.append(leaf(context, table, pending))
                pending, size = [], 0
            pending.append(row)
            size += encoded_size
        if pending or not leaves:
            leaves.append(leaf(context, table, pending))
        while len(leaves) > 1:
            leaves = [branch(context, table, group) for group in _groups(leaves)]
        return cls(context, table, leaves[0])

    def lookup(self, key):
        _check_key(self.table, key)
        node = self.root
        while node.children:
            index = _child_index(node, key)
            node = node.children[index]
        orders = [r.key.order() for r in node.rows]
        index = bisect_left(orders, key.order())
        return node.rows[index] if index < len(node.rows) and node.rows[index].key == key else None

    def put(self, row, *, replace=False):
        """Insert, or explicitly replace an existing PK. Never silently overwrite."""
        _check_row(self.table, row)

        def change(node):
            if not node.children:
                rows = list(node.rows)
                i = bisect_left([r.key.order() for r in rows], row.key.order())
                exists = i < len(rows) and rows[i].key == row.key
                if exists != replace:
                    fail("REJECT_MISSING_PK" if replace else "REJECT_DUPLICATE_PK")
                if exists:
                    if rows[i].raw == row.raw:
                        return [node]  # no representation-only rewrite
                    rows[i] = row
                else:
                    rows.insert(i, row)
                return self._split_leaf(rows)
            children = list(node.children)
            i = _child_index(node, row.key)
            children[i:i+1] = change(children[i])
            return self._split_branch(children)

        roots = change(self.root)
        while len(roots) > 1:
            roots = [branch(self.context, self.table, g) for g in _groups(roots)]
        return Tree(self.context, self.table, roots[0])

    def _split_leaf(self, rows):
        if len(rows) <= LEAF_ROWS and (len(rows) == 1 or _leaf_size(
                self.context, self.table, rows, sum(len(_row_bytes(r)) for r in rows)) <= LEAF_BYTES):
            return [leaf(self.context, self.table, rows)]
        middle = len(rows)//2
        return self._split_leaf(rows[:middle]) + self._split_leaf(rows[middle:])

    def _split_branch(self, children):
        if len(children) <= FANOUT:
            return [branch(self.context, self.table, children)]
        # An oversized replacement may split a leaf repeatedly. Process each
        # 33-child overflow left16/right17, rather than changing the profile.
        left = children[:MIN_FANOUT]
        return [branch(self.context, self.table, left)] + self._split_branch(children[MIN_FANOUT:])

    def delete(self, key):
        _check_key(self.table, key)

        def change(node):
            if not node.children:
                rows = list(node.rows)
                i = bisect_left([r.key.order() for r in rows], key.order())
                if i == len(rows) or rows[i].key != key:
                    fail("REJECT_MISSING_PK")
                rows.pop(i)
                return leaf(self.context, self.table, rows) if rows else None
            children = list(node.children)
            i = _child_index(node, key)
            updated = change(children[i])
            if updated is None:
                children.pop(i)
            else:
                children[i] = updated
                if updated.children and len(updated.children) < MIN_FANOUT:
                    self._rebalance(children, i)
            return branch(self.context, self.table, children) if children else None

        root = change(self.root)
        if root is None:
            root = leaf(self.context, self.table, ())
        while len(root.children) == 1:
            root = root.children[0]
        return Tree(self.context, self.table, root)

    def _rebalance(self, siblings, i):
        node = siblings[i]
        left = siblings[i-1] if i else None
        right = siblings[i+1] if i+1 < len(siblings) else None
        if left and len(left.children) > MIN_FANOUT:
            siblings[i-1] = branch(self.context, self.table, left.children[:-1])
            siblings[i] = branch(self.context, self.table, (left.children[-1],) + node.children)
        elif right and len(right.children) > MIN_FANOUT:
            siblings[i] = branch(self.context, self.table, node.children + (right.children[0],))
            siblings[i+1] = branch(self.context, self.table, right.children[1:])
        elif left:
            siblings[i-1:i+1] = [branch(self.context, self.table, left.children + node.children)]
        elif right:
            siblings[i:i+2] = [branch(self.context, self.table, node.children + right.children)]

    def move(self, old_key, row):
        _check_row(self.table, row)
        if old_key == row.key:
            return self.put(row, replace=True)
        if self.lookup(row.key) is not None:
            fail("REJECT_DUPLICATE_PK")
        return self.delete(old_key).put(row)

    def rows(self):
        def visit(node):
            if node.children:
                for child in node.children:
                    yield from visit(child)
            else:
                yield from node.rows
        return visit(self.root)

    def objects(self):
        def visit(node):
            yield node.object
            for child in node.children:
                yield from visit(child)
        return visit(self.root)

    def validate(self):
        """Expensive full-tree executable invariant oracle (explicit, O(N))."""
        seen, orders = set(), []

        def visit(node, root=False):
            if (type(node.height) is not int or not 0 <= node.height <= 63 or
                    type(node.count) is not int or not 0 <= node.count <= MAX_I64):
                fail("REJECT_NODE_METADATA")
            if node.object.hash in seen:
                fail("REJECT_DUPLICATE_CHILD")
            seen.add(node.object.hash)
            if node.children:
                if not (2 if root else MIN_FANOUT) <= len(node.children) <= FANOUT:
                    fail("REJECT_NODE_BOUNDS")
                for child in node.children:
                    visit(child)
                for left, right in zip(node.children, node.children[1:]):
                    if left.maximum.order() >= right.minimum.order():
                        fail("REJECT_RANGE")
                expected = branch(self.context, self.table, node.children)
            else:
                if not root and not node.rows:
                    fail("REJECT_EMPTY_CHILD")
                for row in node.rows:
                    _check_row(self.table, row)
                    if Row.make(self.table, row.value()) != row:
                        fail("REJECT_ROW")
                    orders.append(row.key.order())
                expected = leaf(self.context, self.table, node.rows)
            if expected != node:
                fail("REJECT_NODE_METADATA")
        visit(self.root, True)
        if any(a >= b for a, b in zip(orders, orders[1:])):
            fail("REJECT_PK_ORDER")
        return len(orders)


def _check_key(table, key):
    if not isinstance(key, Key) or (type(key.value) is int) != (PRIMARY[table] == "id"):
        fail("REJECT_KEY_DOMAIN")


def _check_row(table, row):
    if not isinstance(row, Row) or row.table != table:
        fail("REJECT_TABLE")
    _check_key(table, row.key)


def _child_index(node, key):
    # Gaps go to the left range's successor (or the final child).
    ends = [child.maximum.order() for child in node.children]
    return min(bisect_left(ends, key.order()), len(ends)-1)


def raw_root(context, trees):
    if set(trees) != set(TABLES):
        fail("REJECT_TABLE_COVERAGE")
    for table in TABLES:
        if trees[table].context != context or trees[table].table != table:
            fail("REJECT_ROOT_CONTEXT")
    return Object.make(dict(kind="raw-root", **context.fields(), tables=[
        dict(name=table, root=trees[table].root.descriptor(), count=str(trees[table].root.count))
        for table in TABLES]))
