part of 'verification.dart';

// Canonical path-copy edits of the SAME structural=1 Patricia representation.
// Only changed fact-key paths are read. Complete verification remains the oracle.
class _PatriciaEdit {
  _PatriciaEdit(this.target, this.load, ObjectRef index, this.work) {
    root = ObjectRef.parse(read(index)['facts']);
  }
  final SyncTarget target;
  final ObjectLoader load;
  final SegmentedWork? work;
  final Map<String, Map<String, dynamic>> nodes = {};
  late ObjectRef root;
  Map<String, dynamic> read(ObjectRef ref) => nodes.putIfAbsent(ref.hash, () {
        work?.add('index_nodes_examined');
        return load(ref).body;
      });
  String bits(String hash) => hash
      .split('')
      .map((c) => int.parse(c, radix: 16).toRadixString(2).padLeft(4, '0'))
      .join();
  String common(String a, String b) {
    var i = 0;
    while (i < a.length && i < b.length && a[i] == b[i]) {
      i++;
    }
    return a.substring(0, i);
  }

  String prefix(ObjectRef ref) {
    final node = read(ref);
    return node['kind'] == 'index-leaf'
        ? bits(node['digest'])
        : node['prefix'] as String? ?? '';
  }

  ObjectRef make(String kind, Map<String, dynamic> values) {
    final body = <String, dynamic>{
      'kind': kind,
      'ns': target.ns.toJson(),
      'canon': 1,
      'structural': 1,
      'raw_schema': target.versions.rawSchema,
      ...values
    };
    final bytes = encodeC1(body);
    final ref = ObjectRef.parse(
        {'hash': objectHash(kind, bytes), 'bytes': '${bytes.length}'});
    nodes[ref.hash] = body;
    work?.add('index_nodes_built');
    return ref;
  }

  ObjectRef leaf(String digest, List<Map<String, dynamic>> facts) {
    facts.sort((a, b) => byteCompare(encodeC1(a['key']), encodeC1(b['key'])));
    return make('index-leaf',
        {'digest': digest, 'count': '${facts.length}', 'facts': facts});
  }

  ObjectRef branch(ObjectRef left, ObjectRef right) => make('index-node', {
        'prefix': common(prefix(left), prefix(right)),
        'left': left.toJson(),
        'right': right.toJson(),
        'count':
            '${BigInt.parse(read(left)['count']) + BigInt.parse(read(right)['count'])}'
      });
  void remove(Map<String, dynamic> expected) {
    final path = bits(objectHash('fact-key', encodeC1(expected['key'])));
    ObjectRef? change(ObjectRef ref) {
      final node = read(ref);
      if (node['count'] == '0' || !path.startsWith(prefix(ref))) {
        rejectSegment('DIFF_OLD_MEMBERSHIP_INVALID');
      }
      if (node['kind'] == 'index-leaf') {
        final facts =
            (node['facts'] as List).cast<Map<String, dynamic>>().toList();
        final index = facts.indexWhere(
            (f) => sameBytes(encodeC1(f['key']), encodeC1(expected['key'])));
        if (index < 0 ||
            !sameBytes(encodeC1(facts[index]), encodeC1(expected))) {
          rejectSegment('DIFF_OLD_MEMBERSHIP_INVALID');
        }
        facts.removeAt(index);
        return facts.isEmpty ? null : leaf(node['digest'], facts);
      }
      final left = ObjectRef.parse(node['left']),
          right = ObjectRef.parse(node['right']);
      if (path[(node['prefix'] as String).length] == '0') {
        final next = change(left);
        return next == null ? right : branch(next, right);
      }
      final next = change(right);
      return next == null ? left : branch(left, next);
    }

    root = change(root) ?? make('index-empty', {'count': '0'});
  }

  void put(Map<String, dynamic> fact) {
    final digest = objectHash('fact-key', encodeC1(fact['key'])),
        path = bits(objectHash('fact-key', encodeC1(fact['key'])));
    ObjectRef change(ObjectRef ref) {
      final node = read(ref);
      if (node['count'] == '0') return leaf(digest, [fact]);
      final shared = common(prefix(ref), path);
      if (shared.length < prefix(ref).length) {
        final fresh = leaf(digest, [fact]);
        return path[shared.length] == '0'
            ? branch(fresh, ref)
            : branch(ref, fresh);
      }
      if (node['kind'] == 'index-leaf') {
        final facts =
            (node['facts'] as List).cast<Map<String, dynamic>>().toList();
        if (facts
            .any((f) => sameBytes(encodeC1(f['key']), encodeC1(fact['key'])))) {
          rejectSegment('DIFF_UNIQUE_CONFLICT');
        }
        return leaf(digest, [...facts, fact]);
      }
      final left = ObjectRef.parse(node['left']),
          right = ObjectRef.parse(node['right']);
      return path[(node['prefix'] as String).length] == '0'
          ? branch(change(left), right)
          : branch(left, change(right));
    }

    root = change(root);
  }

  ObjectRef finish() => make(
      'index-root', {'facts': root.toJson(), 'count': read(root)['count']});
}
