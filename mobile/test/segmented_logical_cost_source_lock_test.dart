import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/logical_cost_source_lock.dart';

void main() {
  final root = Directory.current.parent;
  final review = jsonDecode(
      File('${root.path}/docs/benchmarks/t66f-b03/source-lock-review.json')
          .readAsStringSync()) as Map;
  for (final entry in (review['files'] as Map).entries) {
    final path = entry.key as String, file = entry.value as Map;
    test('B03 current exact source and preserved historical revision: $path',
        () {
      final bytes = File('${root.path}/$path').readAsBytesSync();
      expect(sha256.convert(bytes).toString(), file['reviewed_sha256']);
      if (file['historical_sha256'] != null) {
        final restored =
            restoreReviewedB03Source(path, utf8.decode(bytes), review);
        expect(sha256.convert(utf8.encode(restored)).toString(),
            file['historical_sha256']);
        expect(
            () => restoreReviewedB03Source(
                path, '${utf8.decode(bytes)}\n', review),
            throwsStateError,
            reason: 'unreviewed content cannot hide in an exclusion');
      }
    });
  }
}
