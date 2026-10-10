from dataclasses import replace
import random

import pytest

from isolated_sync.canonical import CanonicalError, Context, Key, Namespace, decode_c1
from isolated_sync.raw import Row, TABLES
from isolated_sync.segments import Tree, raw_root


CTX = Context(Namespace("11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222",
                        "33333333-3333-4333-8333-333333333333"), "a" * 64)


def row(i, value="한글😀"):
    return Row.make("app_labels", dict(key=f"{i:08d}", value=value, updated_at="2026-10-05 12:00:00"))


def independent_rows(node):
    """Read the encoded object graph, not Tree.rows or cached node metadata."""
    body = decode_c1(node.object.raw)
    if body["kind"] == "snapshot-leaf":
        return [(item["key"][1], item["value"]) for item in body["rows"]]
    result = []
    for descriptor, child in zip(body["children"], node.children, strict=True):
        assert descriptor["ref"] == child.object.ref()
        result.extend(independent_rows(child))
    return result


@pytest.mark.parametrize("count", [0, 1, 255, 256, 257, 511, 512, 513, 8192, 8193, 10000])
def test_full_tree_profile_and_coverage(count):
    source = [row(i) for i in range(count)]
    tree = Tree.build(CTX, "app_labels", reversed(source))
    assert tree.validate() == count
    assert independent_rows(tree.root) == [(r.key.value, r.value()) for r in source]
    assert tree.root.height == (0 if count <= 256 else 1 if count <= 8192 else 2)


def test_delete_internal_underflow_borrow_merge_collapse():
    tree = Tree.build(CTX, "app_labels", [row(i) for i in range(10000)])
    original = tree
    # Delete complete leaves across both internal nodes, exercising both sides.
    for i in range(10000):
        tree = tree.delete(row(i).key)
        if i % 256 == 255 or i >= 9998:
            assert tree.validate() == 9999-i
    assert tree.root.height == 0 and tree.root.count == 0
    assert original.validate() == 10000  # previous generation wasn't mutated


def test_oversized_singleton_and_replacement_split():
    tree = Tree.build(CTX, "app_labels", [row(i) for i in range(256)])
    tree = tree.put(row(128, "😀" * 70000), replace=True)
    assert tree.validate() == 256
    leaves = [obj.body() for obj in tree.objects() if obj.kind == "snapshot-leaf"]
    large = [v for v in leaves if v["oversized"]]
    assert len(large) == 1 and len(large[0]["rows"]) == 1
    assert tree.lookup(row(128).key).value()["value"] == "😀" * 70000


@pytest.mark.parametrize("seed", [66201, 66202, 66203])
def test_randomized_persistent_mutations(seed):
    rng, expected = random.Random(seed), {}
    tree = Tree.build(CTX, "app_labels")
    for step in range(600):
        i = rng.randrange(400)
        key = row(i).key
        if i in expected and rng.randrange(3) == 0:
            tree = tree.delete(key)
            del expected[i]
        else:
            value = row(i, f"{step} é é 😀")
            tree = tree.put(value, replace=i in expected)
            expected[i] = value.value()
        assert tree.validate() == len(expected)
        assert independent_rows(tree.root) == [(row(k).key.value, expected[k]) for k in sorted(expected)]


def test_pk_movement_duplicate_and_missing_fail_closed():
    tree = Tree.build(CTX, "app_labels", [row(1), row(2)])
    tree = tree.move(row(1).key, row(3))
    assert tree.lookup(row(1).key) is None and tree.lookup(row(3).key) == row(3)
    for action in (lambda: tree.put(row(2)), lambda: tree.put(row(9), replace=True),
                   lambda: tree.delete(row(1).key), lambda: tree.move(row(3).key, row(2)),
                   lambda: tree.lookup(Key(1))):
        with pytest.raises(CanonicalError):
            action()


def test_raw_root_exact_coverage_and_tampered_metadata():
    trees = {name: Tree.build(CTX, name) for name in TABLES}
    root = raw_root(CTX, trees).body()
    assert [v["name"] for v in root["tables"]] == list(TABLES)
    assert all(v["root"]["count"] == "0" for v in root["tables"])
    with pytest.raises(CanonicalError):
        raw_root(CTX, {})
    tree = Tree.build(CTX, "app_labels", [row(1)])
    with pytest.raises(CanonicalError):
        replace(tree, root=replace(tree.root, count=2)).validate()
    with pytest.raises(CanonicalError):
        replace(tree, root=replace(tree.root, count=True)).validate()


def test_exact_byte_boundary_and_oversized_singleton():
    from isolated_sync.segments import LEAF_BYTES
    initial = Tree.build(CTX, "app_labels", [row(1, "")])
    space = LEAF_BYTES-len(initial.root.object.raw)
    exact = Tree.build(CTX, "app_labels", [row(1, "a"*space)])
    assert len(exact.root.object.raw) == LEAF_BYTES
    assert not exact.root.object.body()["oversized"]
    over = Tree.build(CTX, "app_labels", [row(1, "a"*(space+1))])
    assert over.root.object.body()["oversized"]
    assert over.validate() == 1


def test_internal_insert_split_history_identity_and_reused_paths():
    tree = Tree.build(CTX, "app_labels", [row(i) for i in range(8192)])
    old = tree
    tree = tree.put(row(8192))
    assert tree.validate() == 8193 and tree.root.height == 2
    assert [len(c.children) for c in tree.root.children] == [16, 17]
    assert tree.root.children[0].children[0] is old.root.children[0]
    assert tree.put(row(8192), replace=True).root.object == tree.root.object
    # Same logical rows, two valid mutation histories need NOT have one shape.
    tiny = Tree.build(CTX, "app_labels", [row(i) for i in range(256)])
    changed = tiny.put(row(256)).delete(row(256).key)
    assert list(changed.rows()) == list(tiny.rows())
    assert changed.validate() == tiny.validate() == 256
    assert changed.root.object.hash != tiny.root.object.hash


def test_left_internal_borrow_and_cross_leaf_pk_move():
    tree = Tree.build(CTX, "app_labels", [row(i) for i in range(9216)])
    assert [len(c.children) for c in tree.root.children] == [18, 18]
    for i in range(9215, 8447, -1):
        tree = tree.delete(row(i).key)
    assert [len(c.children) for c in tree.root.children] == [17, 16]
    assert tree.validate() == 8448
    tree = tree.move(row(0).key, row(99999))
    assert tree.lookup(row(0).key) is None and tree.lookup(row(99999).key) == row(99999)
    assert tree.validate() == 8448
    for children in (tree.root.children[:-1], (tree.root.children[0],)*2):
        with pytest.raises(CanonicalError):
            replace(tree, root=replace(tree.root, children=children)).validate()
