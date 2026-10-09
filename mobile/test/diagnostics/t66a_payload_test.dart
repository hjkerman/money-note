// Opt-in HOST diagnostic only. No startup/deployment imports this harness.
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/coherent_refresh_models.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

const output = String.fromEnvironment('T66A_OUTPUT');
const withHttp = bool.fromEnvironment('T66A_HTTP');
final owner = AuthUser(
    id: 1,
    username: 'bundle-owner',
    displayName: 'bundle-owner',
    sharePinNeedsChange: false);

OfflineBaseline makeBaseline(CoherentRefreshBundle bundle) {
  final c = bundle.candidate, e = bundle.envelope;
  return OfflineBaseline(
      syncedAt: DateTime.utc(2026, 10, 5, 12),
      user: c.user,
      summary: c.summary,
      cardPaymentStatus: c.cardPaymentStatus,
      judgment: c.judgment,
      monthCloseStatus: c.monthCloseStatus,
      settings: c.settings,
      ownerDiscountMonth: c.ownerDiscountMonth,
      familyDiscountMonth: c.familyDiscountMonth,
      transitDiscountProfile: c.transitDiscountProfile,
      entries: c.entries,
      confirmedPlannedEntries: c.confirmedPlannedEntries,
      panels: c.panels,
      cashFlows: c.cashFlows,
      authoritativeSnapshot: e.snapshot,
      serverStateFingerprint: e.fingerprint,
      discountPolicyDefaults: e.discountPolicyDefaults);
}

double elapsed(Stopwatch watch) => watch.elapsedMicroseconds / 1000;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('T6.6A frozen bytes admission and actual durable HOST pipeline',
      () async {
    final rows = <Map<String, dynamic>>[];
    for (final name in [
      '376',
      '1000',
      '5000',
      '10000',
      'heavy600',
      'varied10000'
    ]) {
      final body = File('$output/body-$name.json').readAsBytesSync();
      final directory = await Directory.systemTemp.createTemp('mn-t66a-store-');
      final store = OfflineStore(directoryProvider: () async => directory);
      try {
        for (var i = 0; i < 23; i++) {
          final total = Stopwatch()..start(), stages = <String, double>{};
          void observe(String key, Duration duration) =>
              stages[key] = duration.inMicroseconds / 1000;
          final parsed = AuthoritativeBundle.decode(body, onStage: observe);
          final bundle = parsed.toCoherentBundle(owner, onStage: observe);
          final parserMs = elapsed(total);
          final baselineStart = Stopwatch()..start();
          final baseline = makeBaseline(bundle);
          final constructionMs = elapsed(baselineStart);
          final encodingStart = Stopwatch()..start();
          final encoded = utf8.encode(jsonEncode(baseline.toJson()));
          final encodeMs = elapsed(encodingStart);
          final publicationStart = Stopwatch()..start();
          await store.replaceBaseline(baseline, beforePublish: () {});
          final publicationMs = elapsed(publicationStart);
          final readStart = Stopwatch()..start();
          final restored = await store.loadBaseline();
          final readMs = elapsed(readStart);
          final totalMs = elapsed(total);
          // Assertions are outside the measured pipeline.
          expect(restored, isNotNull);
          expect(restored!.toJson(), baseline.toJson());
          final durable = File('${directory.path}/offline-mode/baseline.json')
              .readAsBytesSync();
          expect(durable, encoded);
          expect(restored.authoritativeSnapshot, bundle.envelope.snapshot);
          if (i >= 3) {
            rows.add({
              'dataset': name,
              'sample': i - 3,
              'warmups': 3,
              'raw_bytes': body.length,
              'sha256': sha256.convert(body).toString(),
              'stages': stages,
              'parser_typed_ms': parserMs,
              'baseline_construction_ms': constructionMs,
              'baseline_encode_ms': encodeMs,
              'baseline_publish_ms': publicationMs,
              'baseline_readback_ms': readMs,
              'baseline_bytes': durable.length,
              'total_diagnostic_pipeline_ms': totalMs,
            });
          }
        }
      } finally {
        await directory.delete(recursive: true);
      }
    }
    File('$output/client-raw.json').writeAsStringSync(jsonEncode(rows));
  }, skip: output.isEmpty, timeout: const Timeout(Duration(minutes: 15)));

  test('T6.6A actual IOClient content encoding and byte-exact admission',
      () async {
    HttpOverrides.global = null;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
            const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
            (_) async => null);
    final rows = <Map<String, dynamic>>[];
    for (final name in ['376', '1000', '5000', '10000', 'heavy600']) {
      final body = File('$output/body-$name.json').readAsBytesSync();
      final compressed = gzip.encode(body);
      final decompressions = <double>[];
      for (var i = 0; i < 23; i++) {
        final watch = Stopwatch()..start();
        final decoded = gzip.decode(compressed);
        final ms = elapsed(watch);
        expect(decoded, body);
        if (i >= 3) decompressions.add(ms);
      }
      for (final mode in ['identity', 'gzip']) {
        // Unmodified configured API transport; only the synthetic base URL
        // selects a diagnostic wrapper. Each API client reuses its connection.
        final transport = IOClient();
        final api = MoneyNoteApiClient(
            client: transport, baseUrl: 'http://127.0.0.1:18081/$mode/$name');
        await api.saveSession('synthetic-diagnostic-credential');
        try {
          for (var i = 0; i < 23; i++) {
            final watch = Stopwatch()..start();
            final received = await api.authoritativeStateBytes();
            final httpMs = elapsed(watch);
            expect(received, body); // after automatic transport decompression
            final parsed = AuthoritativeBundle.decode(received);
            final candidate = parsed.toCoherentBundle(owner);
            expect(candidate.envelope.snapshot, parsed.wire['snapshot']);
            if (i >= 3) {
              rows.add({
                'dataset': name,
                'mode': mode,
                'sample': i - 3,
                'http_body_available_ms': httpMs,
                'decoded_body_bytes': received.length,
                'decoded_sha256': sha256.convert(received).toString(),
              });
            }
          }
        } finally {
          transport.close();
        }
      }
      rows.add({
        'dataset': name,
        'mode': 'dart_gzip_decode',
        'samples_ms': decompressions,
        'compressed_bytes_dart_default': compressed.length,
      });
    }
    final transport = IOClient();
    final api = MoneyNoteApiClient(
        client: transport, baseUrl: 'http://127.0.0.1:18081/actual/376');
    try {
      await api.saveSession('synthetic-diagnostic-credential');
      for (var i = 0; i < 3; i++) {
        final body = await api.authoritativeStateBytes();
        AuthoritativeBundle.decode(body).toCoherentBundle(owner);
      }
    } finally {
      transport.close();
    }
    File('$output/client-http-raw.json').writeAsStringSync(jsonEncode(rows));
  },
      skip: output.isEmpty || !withHttp,
      timeout: const Timeout(Duration(minutes: 15)));
}
