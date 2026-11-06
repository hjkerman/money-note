@Timeout(Duration(hours: 2))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/api_transport.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../t66f-b02-implementation/verification_profile.dart';
import '../t66f-b03-ic01-p03/timing.dart';

void save(String p, Object? value) => File(
  p,
).writeAsStringSync('${const JsonEncoder.withIndent('  ').convert(value)}\n');

class Loopback extends HttpOverrides {}

IOClient freshHttp(String origin) {
  final native = HttpOverrides.runWithHttpOverrides(
    () => HttpClient(),
    Loopback(),
  )..maxConnectionsPerHost = 1;
  native.badCertificateCallback = (_, host, port) =>
      host == '127.0.0.1' && port == Uri.parse(origin).port;
  return IOClient(native);
}

class BodyResponse extends IOStreamedResponse {
  BodyResponse(this.original, Stream<List<int>> stream)
    : super(
        stream,
        original.statusCode,
        contentLength: original.contentLength,
        request: original.request,
        headers: original.headers,
        isRedirect: original.isRedirect,
        persistentConnection: original.persistentConnection,
        reasonPhrase: original.reasonPhrase,
      );
  final IOStreamedResponse original;
  @override
  Future<Socket> detachSocket() => original.detachSocket();
}

class HttpTimes extends http.BaseClient {
  HttpTimes(this.inner, this.progress, this.phase);
  final Phase phase;
  IOClient inner;
  final void Function(int) progress;
  int issued = 0,
      done = 0,
      headerUs = 0,
      bodyUs = 0,
      bytes = 0,
      errors = 0,
      failedUs = 0;
  Map<String, int> snap() => {
    'issued': issued,
    'complete_bodies': done,
    'header_us': headerUs,
    'send_to_complete_body_us': bodyUs,
    'response_entity_bytes': bytes,
    'errors': errors,
    'failed_send_us': failedUs,
  };
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final w = Stopwatch()..start();
    issued++;
    if (phase.active && phase.firstHttpUs == null) phase.firstHttpUs=phase.watch.elapsedMicroseconds;
    if (issued % 128 == 0) progress(issued);
    try {
      final response = await inner.send(request);
      headerUs += w.elapsedMicroseconds;
      final stream = response.stream.transform(
        StreamTransformer<List<int>, List<int>>.fromHandlers(
          handleData: (v, s) {
            bytes += v.length;
            s.add(v);
          },
          handleError: (Object e, StackTrace st, s) {
            errors++;
            s.addError(e, st);
          },
          handleDone: (s) {
            done++;
            if (phase.active && request.method == 'DELETE') phase.releaseDone=true;
            bodyUs += w.elapsedMicroseconds;
            s.close();
          },
        ),
      );
      return BodyResponse(response, stream);
    } catch (_) {
      errors++;
      failedUs += w.elapsedMicroseconds;
      rethrow;
    }
  }

  @override
  void close() => inner.close();
}

Map<String, int> diff(Map<String, int> a, Map<String, int> b) => {
  for (final k in {...a.keys, ...b.keys}) k: (a[k] ?? 0) - (b[k] ?? 0),
};
int cpuTicks() {
  final f = File('/proc/self/stat')
      .readAsStringSync()
      .split(') ')
      .last
      .split(' ');
  return int.parse(f[11]) + int.parse(f[12]);
}

Map<String, Object?> accepted(AcceptedGeneration a) => {
  'id': a.id,
  'sequence': a.sequence,
  'previous_id': a.previousId,
  'target': a.manifest?.target.toJson(),
};
Map<String, int> dbState(String path) {
  final db = sqlite3.open(path, mode: OpenMode.readOnly);
  try {
    return {
      'objects': db.select('SELECT count(*) n FROM objects').single['n'] as int,
      'body_bytes':
          db
                  .select('SELECT coalesce(sum(length(body)),0) n FROM objects')
                  .single['n']
              as int,
      'generations':
          db.select('SELECT count(*) n FROM generations').single['n'] as int,
    };
  } finally {
    db.close();
  }
}

class Phase {
  final watch=Stopwatch();
  bool active=false,releaseDone=false;
  int? firstHttpUs,e3StartUs,sqlBeforeE3Us;
}
class PhaseDatabase extends TimedDatabase {
  PhaseDatabase(super.inner,this.phase);
  final Phase phase;
  final sqlByStageUs=<String,int>{};
  @override T timed<T>(T Function() f) {
    final stage=LogicalCost.activeStage?.name ?? 'OFF_unattributed';
    final w=Stopwatch()..start();
    try{return super.timed(f);} finally {
      sqlByStageUs.update(stage,(v)=>v+w.elapsedMicroseconds,ifAbsent:()=>w.elapsedMicroseconds);
    }
  }
  @override ResultSet select(String s,[List<Object?> p=const []]) {
    if(phase.active && phase.releaseDone && phase.e3StartUs==null) {
      phase.e3StartUs=phase.watch.elapsedMicroseconds;
      phase.sqlBeforeE3Us=sqlUs;
    }
    return super.select(s,p);
  }
}
class Client {
  Client(
    this.on,
    this.root,
    this.store,
    this.state,
    this.http,
    this.outer,
    this.callback,
    this.sql,
    this.costDb,
    this.phase,
  );
  final bool on;
  final Directory root;
  final SegmentedClientStore store;
  final AppState state;
  final HttpTimes http;
  final PhaseDatabase outer;
  final Phase phase;
  final TimedDatabase? callback;
  final SqlCosts sql;
  final CostDatabase? costDb;
  static Future<Client> create(
    bool on,
    Map init,
    Directory root,
    void Function(int) progress,
  ) async {
    expect(root.existsSync(), false);
    root.createSync();
    final s = SqlCosts();
    PhaseDatabase? outer;
    TimedDatabase? cb;
    final phase=Phase();
    CostDatabase? costDb;
    final target = SyncTarget.parse(init['fixture']['manifest']['target']);
    final setup = LogicalCost();
    SegmentedClientStore open() => SegmentedClientStore.open(
      root,
      CacheNamespace.forTarget(init['origin'], target),
      adapters: true,
      limits: largeVerificationStoreLimits,
      diagnosticDatabaseFactory: (p) {
        final native = sqlite3.open(p);
        if (on) {
          cb = TimedDatabase(native);
          costDb = CostDatabase(cb!, s);
          return outer = PhaseDatabase(costDb!,phase);
        }
        return outer = PhaseDatabase(native,phase);
      },
    );
    final store = on ? setup.run(LogicalCostStage.setup, open) : open();
    setup.close();
    final native = HttpOverrides.runWithHttpOverrides(
      () => HttpClient(),
      Loopback(),
    )..maxConnectionsPerHost = 1;
    native.badCertificateCallback = (_, host, port) =>
        host == '127.0.0.1' && port == Uri.parse(init['origin']).port;
    final http = HttpTimes(IOClient(native), progress,phase);
    final api = MoneyNoteApiClient(client: http, baseUrl: init['origin']);
    await api.saveSession(init['token']);
    final legacy = OfflineStore(directoryProvider: () async => root);
    await legacy.replaceBaseline(baselineFixture());
    await legacy.beginOnlineWrite(1);
    final state = AppState(api, offlineStore: legacy)
      ..user = baselineFixture().user;
    return Client(on, root, store, state, http, outer!, cb, s, costDb,phase);
  }

  void close() {
    state.dispose();
    store.close();
    http.close();
  }
}

Map<String,Object?> fullSemantic(Client h, AcceptedGeneration generation) {
  const tables=['ledger_entries','monthly_panels','cash_flows','card_payment_batches','card_payment_batch_items','card_payment_events','card_payment_allocations','card_payment_deferrals','notification_candidate_registrations','app_settings','app_labels'];
  String primary(String table)=>table=='card_payment_deferrals'?'entry_payment_key':table=='notification_candidate_registrations'?'registration_key':(table=='app_settings'||table=='app_labels')?'key':'id';
  return h.store.withAcceptedRead(generation,(read){
    final values=<String,Object?>{};
    for(final table in tables) {
      TreeKey? after;final rowHashes=StringBuffer();var count=0;
      while(true) {
        final page=read.rows(table,after:after,limit:256);
        if(page.isEmpty)break;
        for(final row in page){rowHashes.writeln(sha256.convert(encodeC1(row)).toString());count++;}
        final key=page.last[primary(table)];after=TreeKey.parse([key is int?'i':'t','$key'],table);
      }
      values[table]={'count':count,'sha256':sha256.convert(utf8.encode(rowHashes.toString())).toString()};
    }
    return {'raw_value_sha256':values,'financial_state_sha256':sha256.convert(encodeC1(read.hot['state'])).toString()};
  });
}
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('B05-A 실제 Flutter cold A/B와 E3/E4',()async{
    const planPath=String.fromEnvironment('B05A_PLAN');
    const smoke=bool.fromEnvironment('B05A_COMPILE_ONLY');
    if(smoke){expect(ReleaseContract.financialEngine,'f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3');return;}
    final plan=jsonDecode(File(planPath).readAsStringSync()) as Map;
    final tree=Directory.current.parent.path;
    FlutterSecureStorage.setMockInitialValues({});
    for(final item in plan['runs'] as List) {
      final cfg=Map<String,dynamic>.from(item as Map);
      final n=cfg['N'] as int;expect([1000,5000],contains(n));
      final out=cfg['out'] as String;
      final scratch=plan['scratch'] as String;
      expect(Directory(out).existsSync(),false);Directory(out).createSync(recursive:true);
      final process=await Process.start('$tree/.venv/bin/python',[plan['server'] as String,'$n','$out/server'],environment:{'B05A_TREE':cfg['backend_tree'] as String,'B05A_VARIANT':cfg['variant'] as String,'B05A_FIXTURE':cfg['fixture'] as String,'TMPDIR':'$scratch/disposable','PYTHONDONTWRITEBYTECODE':'1'});
      final err=File('$out/server.stderr').openWrite();process.stderr.listen(err.add);
      final lines=StreamIterator(process.stdout.transform(utf8.decoder).transform(const LineSplitter()));
      Future<Map<String,dynamic>> command(Map<String,Object?> c)async{process.stdin.writeln(jsonEncode(c));await process.stdin.flush();expect(await lines.moveNext().timeout(const Duration(seconds:60)),true);return jsonDecode(lines.current) as Map<String,dynamic>;}
      Client? client;Object? failure;Map<String,Object?> row={...cfg,'status':'RUNNING','valid_completed':false,'full_client_cold':true,'E2':false,'E1':false,'E3':false,'E4':false};
      save('$out/run.json',row);
      try {
        expect(await lines.moveNext().timeout(const Duration(minutes:2)),true);final init=jsonDecode(lines.current) as Map;
        final on=cfg['on'] as bool;
        final h=await Client.create(on,init,Directory('$scratch/disposable/${cfg['id']}'),(issued)=>save('$out/progress.json',{'id':cfg['id'],'http_issued':issued,'utc':DateTime.now().toUtc().toIso8601String(),'RSS':ProcessInfo.currentRss}));client=h;
        final before=h.store.acceptedGeneration(), dbBefore=dbState(h.store.path);expect(before.id,isNull);expect(before.sequence,0);expect(dbBefore['objects'],0);
        final collector=LogicalCost();
        final sql=h.sql.forCollector(collector);
        final beforeSql=h.outer.sqlUs,beforeCallbacks=h.callback?.callbackUs??0;
        final sqlStagesBefore=Map<String,int>.of(h.outer.sqlByStageUs);final beforeWork=h.store.work.snapshot(),beforeHttp=h.http.snap();
        await command({'command':'mode','on':on,'label':cfg['id']});
        final cpuStart=cpuTicks(),started=DateTime.now().toUtc();
        h.phase.active=true;h.phase.watch.start();
        row.addAll({'start_utc':started.toIso8601String(),'accepted_before':accepted(before),'db_before':dbBefore,'fixture_digest':init['fixture']['fixture_sha256'],'template_sha256':init['fixture']['template_sha256'],'H':{'current_ledger_rows':105,'other_authoritative_rows':35,'hot_bytes':init['fixture']['hot_bytes'],'control_bytes':init['fixture']['control_bytes']},'D':null,'logical_counters':null,'sql_counters':null,'client_admission_engine':ReleaseContract.financialEngine});
        Future<SegmentedPublication> publish()=>h.state.publishSegmentedForIsolatedUse(h.store,verificationLimits:largeVerificationFetchLimits);
        final p=on?await collector.run(LogicalCostStage.e2,publish):await publish();
        final publicationUs=h.phase.watch.elapsedMicroseconds;
        final post=h.store.acceptedGeneration();expect(post.id,p.generationId);expect(post.sequence,1);expect(post.previousId,isNull);expect(post.manifest!.target.toJson(),init['fixture']['manifest']['target']);
        final readWatch=Stopwatch()..start();
        Map boundedRead()=>h.store.withAcceptedRead(post,(r)=>{'ledger':r.rows('ledger_entries',after:TreeKey.parse(['i','1001'],'ledger_entries'),limit:1),'cash':r.rows('cash_flows',after:TreeKey.parse(['i','100'],'cash_flows'),limit:1),'hot_present':r.hot['state'] is Map});
        final visible=on?collector.run(LogicalCostStage.e4Read,boundedRead):boundedRead();
        final readUs=readWatch.elapsedMicroseconds,totalUs=h.phase.watch.elapsedMicroseconds;h.phase.active=false;collector.close();
        final totalSql=h.outer.sqlUs-beforeSql, callbacks=(h.callback?.callbackUs??0)-beforeCallbacks;
        final primarySQLStages=diff(h.outer.sqlByStageUs,sqlStagesBefore),primaryWork=h.store.work.since(beforeWork);
        expect(h.phase.e3StartUs,isNotNull);expect(visible['hot_present'],true);
        final backend=await command({'command':'snapshot'});expect(backend['measurement_complete'],true);expect(backend['issued'],backend['closed']);
        final dbAfter=dbState(h.store.path);expect(dbAfter['objects'],init['fixture']['graph']['objects']);
        final semanticsWatch=Stopwatch()..start();final semantics=fullSemantic(h,post);expect(semantics['raw_value_sha256'],init['fixture']['graph']['raw_value_sha256']);
        final readonly=sqlite3.open(h.store.path,mode:OpenMode.readOnly);
        final staged=readonly.select('SELECT count(*) n FROM staging_objects').single['n'];
        final committed=readonly.select('SELECT object_count FROM generations WHERE id=?',[post.id]).single['object_count'];
        expect(readonly.select('PRAGMA quick_check').single.values.single,'ok');expect(readonly.select('PRAGMA foreign_key_check'),isEmpty);readonly.close();
        row.addAll({'status':'COMPLETED','valid_completed':true,'end_utc':DateTime.now().toUtc().toIso8601String(),'publication_elapsed_us':publicationUs,'end_to_end_with_bounded_E4_us':totalUs,'E2_plus_initial_recovery_envelope_us':h.phase.e3StartUs,'first_HTTP_us':h.phase.firstHttpUs,'E1_SQL_API_us':totalSql,'E1_SQL_API_through_acquisition_us':h.phase.sqlBeforeE3Us!-beforeSql,'SQL_by_logical_stage_us':primarySQLStages,'E3_envelope_us':publicationUs-h.phase.e3StartUs!,'E3_transaction_us':p.transactionMicroseconds,'E3_readback_us':p.readbackMicroseconds,'E4_bounded_read_us':readUs,'semantic_verification_outside_primary_us':semanticsWatch.elapsedMicroseconds,'CPU_us_tick10ms':(cpuTicks()-cpuStart)*10000,'accepted_after':accepted(post),'db_after':dbAfter,'client_db_path':h.store.path,'staged_objects':staged,'committed_generation_objects':committed,'completed_objects':dbAfter['objects'],'collector_closed':collector.isClosed,'logical_counters':on?collector.snapshot():null,'sql_counters':on?sql.snapshot():null,'SQL_callback_us_lower_bound':on?callbacks:null,'backend':backend,'HTTP':diff(h.http.snap(),beforeHttp),'work':primaryWork,'E4_visible':visible,'semantic_digest':semantics,'RSS_bytes':ProcessInfo.currentRss,'peak_RSS_bytes':ProcessInfo.maxRss,'native_SQLite_maps':File('/proc/self/maps').readAsLinesSync().where((s)=>s.contains('libsqlite3.so')).toList(),'E2':true,'E1':true,'E3':true,'E4':true,'observation_expired':(backend['requests'] as List).any((r)=>r['status']==410)});
        final finalBackend=await command({'command':'finish'});row['backend_final']=finalBackend;
      }catch(e){failure=e;row.addAll({'status':'INCOMPLETE','valid_completed':false,'error':'$e','end_utc':DateTime.now().toUtc().toIso8601String()});rethrow;}
      finally{
        save('$out/run.json',row);client?.close();
        try{await command({'command':'exit'});await process.stdin.close();expect(await process.exitCode.timeout(const Duration(seconds:30)),0);}finally{await lines.cancel();await err.flush();await err.close();}
        save('$out/completion.json',{'status':failure==null?'COMPLETED':'INCOMPLETE','server_exit':await process.exitCode});
      }
    }
  });
}
