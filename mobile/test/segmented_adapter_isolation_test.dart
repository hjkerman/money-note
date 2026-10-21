import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/logical_cost_source_lock.dart';

void main() {
  final root = Directory.current.parent;
  String read(String path) => File('${root.path}/$path').readAsStringSync();
  String hash(String path) =>
      sha256.convert(File('${root.path}/$path').readAsBytesSync()).toString();
  final targets =
      (jsonDecode(read('docs/benchmarks/t66e4-p0-audit/worktree-targets.json'))
          as Map)['files'] as Map;
  final protected =
      jsonDecode(read('docs/benchmarks/t66e4-p0-audit/protected-source.json'))
          as Map;
  final b03Review =
      jsonDecode(read('docs/benchmarks/t66f-b03/source-lock-review.json'))
          as Map;
  for (final path
      in targets.keys.where((p) => (p as String).startsWith('mobile/lib/'))) {
    test('audited P0 source remains byte-identical: $path', () {
      final actual = path == 'mobile/lib/src/offline/offline_store.dart'
          ? sha256
              .convert(utf8.encode(
                  restoreReviewedB03Source(path, read(path), b03Review)))
              .toString()
          : hash(path);
      expect(actual, targets[path]['sha256']);
    });
  }
  test('original five historical diagnostic files remain byte-identical', () {
    for (final line in read('docs/benchmarks/t66e4-p0/preserved-history.sha256')
        .split('\n')
        .where((l) => l.isNotEmpty)) {
      final parts = line.split(RegExp(r'\s+'));
      expect(hash(parts.last), parts.first);
    }
  });
  for (final path in [
    'mobile/lib/main.dart',
    'mobile/lib/src/offline/offline_projection.dart',
    'mobile/lib/src/offline/offline_lineage_validator.dart',
    'mobile/lib/src/offline/online_write_state.dart',
    'mobile/lib/src/coherent_refresh_coordinator.dart',
    'mobile/lib/src/local_snapshot_repository.dart',
    'mobile/lib/src/segmented/c1.dart',
    'mobile/lib/src/segmented/transport.dart',
    'mobile/lib/src/segmented/verification.dart',
    'mobile/lib/src/segmented/graph.dart',
    'backend/app/db.py',
    'backend/app/db_migrations.py'
  ]) {
    test('default/legacy/E1/E2/E3 protected source unchanged: $path', () {
      final actual = path == 'mobile/lib/src/segmented/c1.dart'
          ? sha256
              .convert(utf8.encode(
                  restoreReviewedB03Source(path, read(path), b03Review)))
              .toString()
          : hash(path);
      expect(actual, protected[path]['sha256']);
    });
  }
  test(
      'B02/A01/A02 reviewed E2 extension preserves the exact default algorithm',
      () {
    final source = read('mobile/lib/src/segmented/fetch.dart');
    // Preserve the original audit hash, never rewrite historical evidence.
    // Remove only the reviewed explicit-profile seams and bounded helper.
    final restored = source
        .replaceFirst(
            RegExp(
                r'\n    // A02 cold continuation: begin\.[\s\S]*?    // A02 cold continuation: end\.\n'),
            '\n')
        .replaceFirst(
            RegExp(
                r'\n  // A02 active-call helper: begin\.[\s\S]*?  // A02 active-call helper: end\.\n'),
            '')
        .replaceFirst(RegExp(r'\nclass _ColdTargetChanged[\s\S]*?\n}\n'), '')
        .split('\ntypedef _FrontierPath')
        .first
        .replaceFirst(
            RegExp(
                r'\n      : _largeGraphVerification = false;[\s\S]*?  final bool _largeGraphVerification;'),
            ';')
        .replaceFirst('(_largeGraphVerification ? 500000 : 100000)', '100000')
        .replaceFirst('(_largeGraphVerification ? 1000000 : 200000)', '200000')
        .replaceFirst(
            RegExp(
                r'          final frontier = limits\._largeGraphVerification[\s\S]*?              : null;\n'),
            '')
        .replaceFirst(
            '            if (frontier != null) return frontier.load(edge, path);\n',
            '')
        .replaceFirst('          frontier?.finish();\n', '');
    expect(sha256.convert(utf8.encode(restored)).toString(),
        protected['mobile/lib/src/segmented/fetch.dart']['sha256']);
    final reviewed = jsonDecode(read(
            'docs/benchmarks/t66f-b02-a02-correction/source-lock-review.json'))
        as Map;
    expect(
        hash('mobile/lib/src/segmented/fetch.dart'), reviewed['fetch_sha256']);
    expect(hash('mobile/lib/src/segmented/protocol.dart'),
        reviewed['protocol_sha256']);
  });
  test(
      'E3 publisher extension is only pre-BEGIN read-scope rejection, guard/COMMIT unchanged',
      () {
    final source = read('mobile/lib/src/segmented/store_publication.dart');
    final exclusion = RegExp(
        r'        // E4 frozen exclusion: begin[\s\S]*?        // E4 frozen exclusion: end\n');
    expect(exclusion.allMatches(source).length, 1);
    const query =
        "        adaptersEnabled\n            ? 'SELECT id FROM generations WHERE id IS NOT ? AND id IS NOT ? AND id NOT IN (SELECT generation_id FROM frozen) AND id NOT IN (SELECT generation_id FROM installed UNION SELECT previous_id FROM installed WHERE previous_id IS NOT NULL)'\n            : 'SELECT id FROM generations WHERE id IS NOT ? AND id IS NOT ?',";
    expect(source.contains(query), true);
    final restored = source
        .replaceFirst('    _requireNoAcceptedReader();\n', '')
        .replaceFirst(exclusion, '')
        .replaceFirst(query,
            "        'SELECT id FROM generations WHERE id IS NOT ? AND id IS NOT ?',");
    expect(sha256.convert(utf8.encode(restored)).toString(),
        protected['mobile/lib/src/segmented/store_publication.dart']['sha256']);
    expect(source,
        contains("finalAuthorityFence();\n      _db.execute('COMMIT');"));
  });
  test(
      'AppState E4 entry has no automatic callers or legacy publication/acknowledgment',
      () {
    final source = read('mobile/lib/src/app_state.dart');
    expect(
        RegExp('readSegmentedForIsolatedUse\\(').allMatches(source).length, 1);
    final begin = source.indexOf('  // Explicit isolated E4 read only.');
    final end =
        source.indexOf('  Future<void> _refreshAuthoritativeState(', begin);
    final seam = source.substring(begin, end);
    for (final forbidden in [
      'replaceBaseline(',
      'completeOnlineWrite(',
      'saveMetadata(',
      'appendOperation(',
      'notifyListeners(',
      'serverStateFingerprint =',
      'summary =',
      'enterOfflineMode('
    ]) {
      expect(seam.contains(forbidden), false, reason: forbidden);
    }
    final installBegin =
        source.indexOf('  // Explicit E4 legacy boundary only.');
    expect(installBegin, greaterThan(0));
    expect(
        RegExp('installSegmentedLegacyForIsolatedUse\\(')
            .allMatches(source)
            .length,
        1);
    final reviewedOriginal = restoreReviewedB03Source(
        'mobile/lib/src/app_state.dart', source, b03Review);
    final originalBegin =
        reviewedOriginal.indexOf('  // Explicit E4 legacy boundary only.');
    final originalEnd = reviewedOriginal.indexOf(
        '  Future<void> _refreshAuthoritativeState(', originalBegin);
    final original = (reviewedOriginal.substring(
                0, originalBegin) +
            reviewedOriginal.substring(originalEnd))
        .replaceFirst(
            '      SyncCancellation? cancellation,\n      FetchLimits verificationLimits = const FetchLimits()}) async {',
            '      SyncCancellation? cancellation}) async {')
        .replaceFirst(
            '      final fetcher =\n          IncrementalFetcher(store, transport, limits: verificationLimits);\n      final acquired = await fetcher.acquire(',
            '      final acquired = await IncrementalFetcher(store, transport).acquire(')
        .replaceFirst("import 'segmented/adapters.dart';\n", '')
        .replaceFirst("import 'segmented/verification.dart';\n", '');
    expect(sha256.convert(utf8.encode(original)).toString(),
        protected['mobile/lib/src/app_state.dart']['sha256']);
  });
}
