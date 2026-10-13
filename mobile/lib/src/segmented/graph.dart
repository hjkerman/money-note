// Acquisition graph closure only. NOT F(raw), financial validation, or E3's
// CompleteTargetVerified/publication receipt. No payloads retained in summaries.
import 'dart:typed_data';
import 'dart:collection';

import 'c1.dart';
import 'object.dart';
import 'protocol.dart';
import 'work.dart';

class GraphClosure {
  const GraphClosure(this.objects, this.edges, this.tableRows,
      [this.provenance]);
  final List<ObjectRef> objects;
  final int edges;
  final Map<String, String> tableRows;
  final GraphProvenance? provenance;
}

// Complete typed-subtree integrity evidence, NOT authorization. The store may
// reuse it only within a recovered connection/session freshness boundary.
class GraphProvenance {
  GraphProvenance._(this.target, this._nodes);
  final SyncTarget target;
  // Append-only summaries of fully verified subtrees; no financial payloads.
  final Map<String, _Summary> _nodes;
  bool contains(ObjectRef ref) => _nodes[ref.hash]?.ref.matches(ref) ?? false;
}

class _GraphRefs extends ListBase<ObjectRef> {
  _GraphRefs(this.roots, this.nodes, this._length);
  final List<ObjectRef> roots;
  final Map<String, _Summary> nodes;
  final int _length;
  @override
  int get length => _length;
  @override
  set length(int value) => throw UnsupportedError('immutable graph');
  @override
  void operator []=(int index, ObjectRef value) =>
      throw UnsupportedError('immutable graph');
  @override
  ObjectRef operator [](int index) {
    if (index < 0 || index >= length) throw RangeError.index(index, this);
    ObjectRef seek(ObjectRef ref, int n) {
      if (n == 0) return ref;
      n--;
      for (final child in nodes[ref.hash]!.children) {
        final count = nodes[child.ref.hash]!.objectCount;
        if (n < count) return seek(child.ref, n);
        n -= count;
      }
      throw StateError('verified graph count');
    }

    for (final ref in roots) {
      final count = nodes[ref.hash]!.objectCount;
      if (index < count) return seek(ref, index);
      index -= count;
    }
    throw StateError('verified graph roots');
  }

  @override
  Iterator<ObjectRef> get iterator => _iterate().iterator;
  Iterable<ObjectRef> _iterate() sync* {
    final pending = roots.reversed.toList();
    while (pending.isNotEmpty) {
      final ref = pending.removeLast();
      yield ref;
      pending.addAll(nodes[ref.hash]!.children.reversed.map((e) => e.ref));
    }
  }
}

class _Summary {
  _Summary(this.ref, this.kind, this.count, this.table, this.descriptor,
      this.prefix, this.children, this.rootChildren, this.tableRows);
  final ObjectRef ref;
  final String kind;
  final BigInt count;
  final String? table;
  final Uint8List? descriptor;
  String prefix;
  final List<TypedObjectReference> children;
  final bool rootChildren;
  final Map<String, String> tableRows;
  int objectCount = 1, edgeCount = 0;
  Uint8List? hotContext;
}

String _bits(String digest) => [
      for (var i = 0; i < digest.length; i++)
        int.parse(digest[i], radix: 16).toRadixString(2).padLeft(4, '0')
    ].join();
String _common(String a, String b) {
  var i = 0;
  while (i < a.length && i < b.length && a[i] == b[i]) {
    i++;
  }
  return a.substring(0, i);
}

_Summary _summarize(VerifiedObject object, SyncTarget target) {
  final body = object.body, kind = object.kind;
  if (kind == 'hot' &&
      !sameBytes(
          encodeC1(body['context']), encodeC1(target.context.toJson()))) {
    rejectSegment('GRAPH_CONTEXT_INVALID');
  }
  final tree = kind.startsWith('snapshot-');
  final rows = <String, String>{};
  if (kind == 'raw-root') {
    for (final entry in body['tables']) {
      rows[entry['name'] as String] = entry['count'] as String;
    }
  }
  return _Summary(
      object.ref,
      kind,
      BigInt.parse(body['count'] as String? ?? '0'),
      tree ? body['table'] as String : null,
      tree
          ? encodeC1({
              for (final f in ['height', 'count', 'min', 'max']) f: body[f]
            })
          : null,
      kind == 'index-leaf'
          ? _bits(body['digest'] as String)
          : kind == 'index-node'
              ? body['prefix'] as String
              : '',
      object.children,
      kind == 'raw-root',
      rows);
}

void _membership(TypedObjectReference edge, _Summary child, bool root) {
  if (!edge.ref.matches(child.ref) ||
      !edge.kinds.contains(child.kind) ||
      (edge.table != null && edge.table != child.table)) {
    rejectSegment('GRAPH_EDGE_INVALID');
  }
  final d = edge.descriptor;
  if (d != null) {
    Object? key(TreeKey? k) => k == null ? null : [k.tag, k.value];
    if (!sameBytes(
        child.descriptor!,
        encodeC1({
          'height': d.height,
          'count': d.count.toString(),
          'min': key(d.minimum),
          'max': key(d.maximum)
        }))) {
      rejectSegment('GRAPH_DESCRIPTOR_INVALID');
    }
    if (!root && d.count == 0) rejectSegment('GRAPH_EMPTY_CHILD');
  }
  if (!root && child.kind == 'snapshot-node' && child.children.length < 16) {
    rejectSegment('GRAPH_FANOUT_INVALID');
  }
}

Future<GraphClosure> verifyAcquisitionGraph(
    SyncTarget target,
    Future<VerifiedObject> Function(
            TypedObjectReference edge, List<String> path)
        load,
    {required int maxObjects,
    required int maxEdges,
    int maxPath = 512,
    GraphProvenance? reuse,
    SegmentedWork? work}) async {
  if (reuse != null &&
      (!reuse.target.ns.matches(target.ns) ||
          reuse.target.principalId != target.principalId ||
          !sameBytes(encodeC1(reuse.target.versions.toJson()),
              encodeC1(target.versions.toJson())))) {
    rejectSegment('GRAPH_PROVENANCE_CONTEXT');
  }
  final seen = <String, _Summary>{};
  final visiting = <String>{};
  var edgeCount = 0;
  Future<_Summary> visit(
      TypedObjectReference edge, List<String> path, bool root) async {
    if (path.length > maxPath || path.length > 512) {
      rejectSegment('GRAPH_DEPTH_BUDGET');
    }
    if (visiting.contains(edge.ref.hash)) rejectSegment('GRAPH_CYCLE');
    final reused = reuse?._nodes[edge.ref.hash];
    if (reused != null) {
      _membership(edge, reused, root);
      if (reused.kind == 'hot' &&
          !sameBytes(reused.hotContext!, encodeC1(target.context.toJson()))) {
        rejectSegment('GRAPH_CONTEXT_INVALID');
      }
      work?.add('graph_reused_subtrees');
      return reused;
    }
    final prior = seen[edge.ref.hash];
    if (prior != null) {
      _membership(edge, prior, root);
      return prior;
    }
    if (seen.length + visiting.length >= maxObjects) {
      rejectSegment('GRAPH_OBJECT_BUDGET');
    }
    visiting.add(edge.ref.hash);
    // Drop raw bytes/parsed rows before descending. Only compact typed refs,
    // descriptor/count/prefix metadata survive an await of a descendant.
    VerifiedObject? object = await load(edge, List.unmodifiable(path));
    work?.add('graph_nodes_examined');
    final node = _summarize(object, target);
    if (node.kind == 'hot') node.hotContext = encodeC1(object.body['context']);
    object = null;
    _membership(edge, node, root);
    final childSummaries = <_Summary>[];
    for (final child in node.children) {
      if (++edgeCount > maxEdges) rejectSegment('GRAPH_EDGE_BUDGET');
      childSummaries.add(
          await visit(child, [...path, child.ref.hash], node.rootChildren));
    }
    if (node.kind == 'index-root') {
      if (childSummaries.single.count != node.count) {
        rejectSegment('GRAPH_INDEX_COUNT');
      }
      node.prefix = childSummaries.single.prefix;
    } else if (node.kind == 'index-node') {
      final left = childSummaries[0], right = childSummaries[1];
      if (left.count <= BigInt.zero ||
          right.count <= BigInt.zero ||
          left.count + right.count != node.count ||
          !left.prefix.startsWith('${node.prefix}0') ||
          !right.prefix.startsWith('${node.prefix}1') ||
          _common(left.prefix, right.prefix) != node.prefix) {
        rejectSegment('GRAPH_PATRICIA_INVALID');
      }
    }
    visiting.remove(edge.ref.hash);
    node.objectCount +=
        childSummaries.fold<int>(0, (n, s) => n + s.objectCount);
    node.edgeCount = childSummaries.length +
        childSummaries.fold<int>(0, (n, s) => n + s.edgeCount);
    seen[edge.ref.hash] = node;
    return node;
  }

  final raw = await visit(
      TypedObjectReference(target.roots['raw']!, {'raw-root'}),
      [target.roots['raw']!.hash],
      true);
  final roots = <_Summary>[raw];
  for (final role in ['index', 'hot', 'control']) {
    final ref = target.roots[role]!;
    roots.add(await visit(
        TypedObjectReference(ref, {role == 'index' ? 'index-root' : role}),
        [ref.hash],
        true));
  }
  final count = roots.fold<int>(0, (n, s) => n + s.objectCount);
  final edges = roots.fold<int>(0, (n, s) => n + s.edgeCount);
  if (count > maxObjects || edges > maxEdges) {
    rejectSegment('GRAPH_OBJECT_BUDGET');
  }
  if (reuse == null && count != seen.length) {
    rejectSegment('GRAPH_DUPLICATE_CHILD');
  }
  final nodes = reuse?._nodes ?? <String, _Summary>{};
  nodes.addAll(seen);
  final evidence = GraphProvenance._(target, nodes);
  return GraphClosure(
      reuse == null
          ? List.unmodifiable(seen.values.map((n) => n.ref))
          : _GraphRefs(
              List.unmodifiable(roots.map((s) => s.ref)), nodes, count),
      edges,
      Map.unmodifiable(raw.tableRows),
      evidence);
}
