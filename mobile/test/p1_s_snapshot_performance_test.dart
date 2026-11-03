// P1-S pre-implementation CPU gate; only explicit host calibration runs it.
import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';

void _validateEnvelope(List<int> bytes) {
  final decoded = jsonDecode(utf8.decode(bytes));
  if (decoded is! Map<String, dynamic> ||
      decoded['schema_version'] is! int ||
      decoded['range'] is! Map ||
      decoded['data'] is! Map ||
      decoded['card_charge_policy'] is! Map ||
      decoded['manifest'] is! Map ||
      decoded['manifest']['tables'] is! Map ||
      decoded['manifest']['content_sha256'] is! String ||
      !RegExp(r'^[0-9a-f]{64}$')
          .hasMatch(decoded['manifest']['content_sha256'] as String)) {
    throw const FormatException('snapshot envelope is incomplete');
  }
}

void main() {
  test('P1-S content receipt digest/decode cost precondition', () async {
    final production = File(
        '${Directory.current.parent.path}/mobile/lib/src/local_snapshot_repository.dart');
    expect(sha256.convert(await production.readAsBytes()).toString(),
        '316c491e512873b500e5417a4b5dff4ebf8885d6a398d5a57cf63b2c28d25432',
        reason: 'This calibration is for the verified baseline before-image.');
    final root = Directory(Platform.environment['P1S_FIXTURES']!);
    final fixture = <int, List<int>>{};
    for (final n in [5000, 10000]) {
      fixture[n] = await File('${root.path}/snapshot-$n.json').readAsBytes();
      _validateEnvelope(fixture[n]!);
    }
    final samples = <Map<String, Object?>>[];
    final identities = [
      for (final n in fixture.keys)
        {
          'rows': n,
          'bytes': fixture[n]!.length,
          'sha256': sha256.convert(fixture[n]!).toString()
        }
    ];
    final watch = Stopwatch()..start();
    Digest? lastDigest;
    bool exhausted = false;
    try {
      for (final block in [1, 2, 3]) {
        for (final n in fixture.keys) {
          final bytes = fixture[n]!;
          for (final op
              in block.isOdd ? ['decode', 'digest'] : ['digest', 'decode']) {
            for (var i = -5; i < 20; i++) {
              final sampleWatch = Stopwatch()..start();
              if (op == 'decode') {
                _validateEnvelope(bytes);
              } else {
                lastDigest = sha256.convert(bytes);
              }
              sampleWatch.stop();
              if (i >= 0) {
                samples.add({
                  'block': block,
                  'rows': n,
                  'operation': op,
                  'sample': i,
                  'elapsed_us': sampleWatch.elapsedMicroseconds
                });
              }
              if (watch.elapsed.inSeconds >= 60) {
                exhausted = true;
                throw StateError('P1-S calibration 60s budget exceeded');
              }
            }
          }
        }
      }
      expect(lastDigest, isNotNull);
    } finally {
      await File(Platform.environment['P1S_OUTPUT']!).writeAsString(jsonEncode({
        'fixtures': identities,
        'samples': samples,
        'elapsed_s': watch.elapsedMilliseconds / 1000,
        'budget_exhausted': exhausted,
        'scope':
            'CPU-only exact original UTF8/JSON/envelope versus SHA256; no I/O; extra bookkeeping excluded',
        'source_sha256':
            '316c491e512873b500e5417a4b5dff4ebf8885d6a398d5a57cf63b2c28d25432'
      }));
    }
  },
      skip: !Platform.environment.containsKey('P1S_OUTPUT'),
      timeout: const Timeout(Duration(seconds: 90)));
}
