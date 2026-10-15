import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/api_transport.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';

import 'offline_mode_fixtures.dart';
import 'segmented_e2_fixture.dart';

class TargetedApi extends MoneyNoteApiClient {
  TargetedApi(this.bridge, this.wire)
      : super(client: bridge, baseUrl: syntheticOrigin);
  final BackendBridge bridge;
  final Map<String, dynamic> wire;
  @override
  Future<void> health({Duration timeout = const Duration(seconds: 15)}) async {}
  @override
  Future<void> logout() => saveSession(null);
  @override
  Future<AuthUser> login(String username, String password) async {
    await saveSession('${bridge.token}-reauthenticated');
    return baselineFixture().user;
  }

  @override
  Future<Uint8List> authoritativeStateBytes() async =>
      Uint8List.fromList(utf8.encode(jsonEncode(wire)));
  @override
  Future<AppSettings> updateSetting(String key, String value) async =>
      AppSettings(values: {key: value});
}

class PausedWorkspace extends E4Workspace {
  PausedWorkspace(super.root, {super.fault});
  Completer<void>? entered, release;
  void pauseRename() {
    entered = Completer();
    release = Completer();
  }

  @override
  Future<void> replaceBaseline(OfflineBaseline baseline,
      {void Function()? beforePublish}) async {
    if (entered != null && !entered!.isCompleted) {
      entered!.complete();
      await release!.future;
    }
    await super.replaceBaseline(baseline, beforePublish: beforePublish);
  }
}

class E4Harness {
  E4Harness._(this.root, this.store, this.workspace, this.api, this.state);
  final Directory root;
  SegmentedClientStore store;
  final PausedWorkspace workspace;
  final TargetedApi api;
  final AppState state;
  File get baselineFile =>
      File('${workspace.root.path}/offline-mode/baseline.json');
  File get pendingFile =>
      File('${workspace.root.path}/offline-mode/online-write-1.json');
  static Future<E4Harness> create(
      BackendBridge bridge, Map<String, dynamic> wire,
      {void Function(String)? fault, StoreFault? sqlFault}) async {
    FlutterSecureStorage.setMockInitialValues({});
    final root = Directory.systemTemp.createTempSync('mn-e4-targeted-');
    final store = SegmentedClientStore.open(
        root, GenerationFixture(bridge.fixture).cache,
        adapters: true, fault: sqlFault);
    final workspace = PausedWorkspace(root, fault: fault);
    await workspace.replaceBaseline(baselineFixture());
    final api = TargetedApi(bridge, wire);
    await api.saveSession(bridge.token);
    final state = AppState(api, offlineStore: workspace)
      ..user = baselineFixture().user;
    return E4Harness._(root, store, workspace, api, state);
  }

  Future<E4LegacyInstallation> install() =>
      state.installSegmentedLegacyForIsolatedUse(store);
  Future<void> publish() async {
    final base = await store.recoverAcceptedGeneration();
    final fetched =
        await IncrementalFetcher(store, segmentedTransportForApi(api))
            .acquire(verifiedBase: base);
    final version = store.publicationDataVersion;
    final proof = await store.verifyPublicationCandidate(fetched.manifest, base,
        verifiedDataVersion: version);
    final p = store.prepareGeneration(
        syncUuid(), fetched.stagingId, proof, base,
        verifiedDataVersion: version);
    store.commitPreparedGeneration(p, finalAuthorityFence: () {});
  }

  void reopen() {
    final cache = store.cache;
    store.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
  }

  void dispose() {
    state.dispose();
    store.close();
    root.deleteSync(recursive: true);
  }
}

Future<Map<String, dynamic>> e4WireOracle() async {
  final repo = Directory.current.parent.path;
  final p = await Process.run('$repo/.venv/bin/python',
      ['$repo/mobile/test/support/e4_backend_oracle.py']);
  if (p.exitCode != 0) {
    throw StateError('synthetic backend oracle failed: ${p.stderr}');
  }
  return jsonDecode(p.stdout as String)['wire'] as Map<String, dynamic>;
}
