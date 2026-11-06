import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:sqlite3/sqlite3.dart';

void main() {
  test('historical namespace cannot replace deleted P03 backend authority', () {
    final repo = Directory.current.parent.path;
    final here = '$repo/docs/benchmarks/t66f-b03-ic01-p04/evidence';
    final p03 =
        jsonDecode(File('$here/clone-plan.json').readAsStringSync()) as Map;
    final target = SyncTarget.parse((p03['manifest'] as Map)['target']);
    final origin =
        (jsonDecode(
              File('$here/recovered-synthetic-origin.json').readAsStringSync(),
            ) as Map)['origin']
            as String;
    final cache = CacheNamespace.forTarget(origin, target);
    const historical = '/tmp/mn-b02-independent-100000-z6ux9y53';
    final old = jsonDecode(
      File('$historical/server/backend-fixture.json').readAsStringSync(),
    ) as Map;
    final previous = SyncTarget.parse((old['manifest'] as Map)['target']);
    expect(previous.ns.matches(target.ns), false);
    final paths = Directory('$historical/client/segmented-store-v1')
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.sqlite'))
        .toList();
    expect(paths.length, 1);
    final d = sqlite3.open(paths.single.path, mode: OpenMode.readOnly);
    try {
      final ref = previous.roots['raw']!;
      final bytes =
          d.select('SELECT body FROM objects WHERE hash=?', [
                ref.hash,
              ]).single['body']
              as List<int>;
      expect(
        () => VerifiedObject.verify(bytes, ref, cache),
        throwsA(
          isA<SegmentedException>().having(
            (e) => e.code,
            'namespace fence',
            'CACHE_CONTEXT_MISMATCH',
          ),
        ),
      );
    } finally {
      d.close();
    }
  });
}
