@Timeout(Duration(minutes: 10))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/online_write_state.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import 'harness.dart';

class ParkPending extends E4Workspace {
  ParkPending(super.root);
  bool park = false;
  final entered = Completer<void>(), release = Completer<void>();
  @override
  Future<PendingOnlineWrite?> loadPendingOnlineWrite(int userId) async {
    if (park) {
      park = false;
      entered.complete();
      await release.future;
    }
    return super.loadPendingOnlineWrite(userId);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('C-L01 real acquired candidate waits on original lineage lock then loses principal', () async {
    final b = await RealBackend.start(2);
    late ParkPending w;
    final h = await RealHarness.create(
      b,
      maxConnections: 2,
      workspaceFactory: (root) => w = ParkPending(root),
    );
    Object? oldError;
    final cancel = SyncCancellation();
    try {
      final before = h.disk();
      await b.command({'command': 'pause', 'path': '/objects'});
      final old = h.state
          .refreshSegmentedForIsolatedUse(h.store, cancellation: cancel)
          .then(
            (_) {},
            onError: (Object e) {
              oldError = e;
            },
          );
      await b.waitEntered();
      w.park = true;
      final mutation = h.state.createCashFlow(
        occurredOn: '2026-10-05',
        title: 'lineage barrier',
        amount: 1,
        isIncome: false,
        isPrimaryIncome: false,
      );
      await w.entered.future.timeout(const Duration(seconds: 10));
      await b.command({'command': 'release'});
      final elapsed = Stopwatch()..start();
      var prepared = false;
      while (elapsed.elapsed < const Duration(minutes: 4)) {
        final db = sqlite3.open(h.store.path);
        try {
          prepared =
              (db.select('SELECT count(*) AS n FROM generations').single['n']
                  as int) ==
              1;
        } finally {
          db.close();
        }
        if (prepared) break;
        await Future<void>.delayed(const Duration(milliseconds: 5));
      }
      expect(
        prepared,
        isTrue,
        reason: 'durable prepared generation while accepted is null proves lock wait',
      );
      final waiting = h.disk();
      expect((waiting['accepted'] as List).single['current_id'], isNull);
      expect((waiting['accepted'] as List).single['sequence'], 0);
      h.state.user = AuthUser(
        id: 2,
        username: 'other',
        displayName: 'other',
        sharePinNeedsChange: false,
      );
      w.release.complete();
      await mutation;
      await old;
      expect(oldError, isNotNull);
      expect(h.disk(), before);
      File(const String.fromEnvironment('C_LINEAGE_OUTPUT')).writeAsStringSync(
        jsonEncode({
          'id': 'C-L01',
          'before': before,
          'waiting': waiting,
          'after': h.disk(),
          'error': '$oldError',
          'wire': await b.stats(),
        }),
      );
    } finally {
      cancel.cancel();
      if (!w.release.isCompleted) w.release.complete();
      await b.command({'command': 'release'});
      h.dispose();
      await b.dispose();
    }
  });
}
