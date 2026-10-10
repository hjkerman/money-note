from dataclasses import replace
import random

import pytest

from isolated_sync.canonical import CanonicalError, encode
from isolated_sync.patricia import Fact, Index, common
from tests.isolated_sync_reference import patricia_root
from tests.test_isolated_sync_segments import CTX


@pytest.mark.parametrize("count", [0, 1, 2, 32, 257, 1000])
def test_reference_and_insertion_order(count):
    facts = [Fact.make(["pk", "app_labels", ["t", str(i)]], f"value {i} 😀") for i in range(count)]
    expected = patricia_root(CTX, facts)
    for seed in range(3):
        shuffled = facts[:]
        random.Random(seed).shuffle(shuffled)
        full = Index.build(CTX, shuffled)
        incremental = Index.build(CTX)
        for fact in shuffled:
            incremental = incremental.put(fact)
        assert full.validate() == incremental.validate() == count
        assert full.object().ref() == incremental.object().ref() == expected
        assert {f.key: f.value for f in full.facts()} == {f.key: f.value for f in facts}


@pytest.mark.parametrize("seed", [66211, 66212, 66213])
def test_randomized_index(seed):
    rng, expected, index = random.Random(seed), {}, Index.build(CTX)
    for step in range(500):
        key = ["pk", "app_labels", ["t", str(rng.randrange(100))]]
        raw = encode(key)
        before = index
        if raw in expected and rng.randrange(3) == 0:
            index = index.delete(key)
            del expected[raw]
            assert index.lookup(key) is None
        else:
            fact = Fact.make(key, str(step))
            index = index.put(fact, replace=raw in expected)
            expected[raw] = fact
            assert index.lookup(key) == fact
        assert index.validate() == len(expected)
        assert index.object().ref() == patricia_root(CTX, list(expected.values()))
        assert before.object().hash != index.object().hash
    for fact in list(expected.values()):
        import json
        index = index.delete(json.loads(fact.key))
    assert index.validate() == 0


def test_long_prefix_one_bit_divergence_and_collisions(monkeypatch):
    import isolated_sync.patricia as module
    real_hash = module.hash_bytes
    digests = {encode(["a"]): "0" * 64, encode(["b"]): "0" * 63 + "1",
               encode(["c"]): "0" * 64, encode([]): "f" * 64}
    monkeypatch.setattr(module, "hash_bytes", lambda kind, raw: digests[raw]
                        if kind == "fact-key" else real_hash(kind, raw))
    facts = [Fact.make([k], k) for k in "abc"] + [Fact.make([], None)]
    index = Index.build(CTX)
    for fact in reversed(facts):
        index = index.put(fact)
    assert common("000", "0001") == "000"
    assert index.validate() == 4
    assert index.object().ref() == patricia_root(CTX, facts, digests.__getitem__)
    assert any(o.body().get("prefix") == "0"*255 for o in index.objects())
    for fact in facts:
        assert index.lookup(fact.wire()["key"]) == fact
        index = index.delete(fact.wire()["key"])
        index.validate()
    assert index.root.count == 0


def test_duplicate_missing_and_tampered_index():
    fact = Fact.make(["pk", "app_labels", ["t", "x"]], "a")
    index = Index.build(CTX, [fact])
    for action in (lambda: Index.build(CTX, [fact, fact]), lambda: index.put(fact),
                   lambda: Index.build(CTX).put(fact, replace=True), lambda: index.delete(["missing"]),
                   lambda: replace(index, root=replace(index.root, count=True)).validate(),
                   lambda: replace(index, root=replace(index.root, count=2)).validate()):
        with pytest.raises(CanonicalError):
            action()
