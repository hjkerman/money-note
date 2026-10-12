// Acquisition graph closure only. NOT F(raw), financial validation, or E3's
// CompleteTargetVerified/publication receipt. No payloads retained in summaries.
import 'dart:typed_data';

import 'c1.dart';
import 'object.dart';
import 'protocol.dart';

class GraphClosure {
  const GraphClosure(this.objects, this.edges, this.tableRows);
  final List<ObjectRef> objects;
  final int edges;
  final Map<String, String> tableRows;
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
    int maxPath = 512}) async {
  final seen = <String, _Summary>{};
  final visiting = <String>{};
  var edgeCount = 0;
  Future<_Summary> visit(
      TypedObjectReference edge, List<String> path, bool root) async {
    if (path.length > maxPath || path.length > 512) {
      rejectSegment('GRAPH_DEPTH_BUDGET');
    }
    if (visiting.contains(edge.ref.hash)) rejectSegment('GRAPH_CYCLE');
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
    final node = _summarize(object, target);
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
    seen[edge.ref.hash] = node;
    return node;
  }

  final raw = await visit(
      TypedObjectReference(target.roots['raw']!, {'raw-root'}),
      [target.roots['raw']!.hash],
      true);
  for (final role in ['index', 'hot', 'control']) {
    final ref = target.roots[role]!;
    await visit(
        TypedObjectReference(ref, {role == 'index' ? 'index-root' : role}),
        [ref.hash],
        true);
  }
  return GraphClosure(List.unmodifiable(seen.values.map((n) => n.ref)),
      edgeCount, Map.unmodifiable(raw.tableRows));
}
