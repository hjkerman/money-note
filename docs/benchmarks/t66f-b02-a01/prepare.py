"""기존 B02 하네스에서 제품 경로/조건을 보존한 조사용 복사본 생성."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
source = (
    ROOT / "docs/benchmarks/t66f-b02-implementation/large_http_test.dart"
).read_text()
source = source.replace(
    "import 'package:http/io_client.dart';",
    "import 'package:http/io_client.dart';\nimport 'package:http/http.dart' as http_api;",
)
source = source.replace(
    "import 'verification_profile.dart';",
    "import '../t66f-b02-implementation/verification_profile.dart';",
)
source = source.replace("t66f-b02-implementation/server.py", "t66f-b02-a01/server.py")
source = source.replace(
    "class _RealLoopback extends HttpOverrides {}",
    r"""class _RealLoopback extends HttpOverrides {}

// Original IOStreamedResponse is returned unchanged: detachSocket/drain semantics
// and E2-A01 cleanup are not replaced. Only request-to-response-header timing.
class _MeterIOClient extends IOClient {
  _MeterIOClient(super.client, this.trace, this.clock);
  final IOSink trace;
  final Stopwatch clock;
  int serial = 0;
  @override
  Future<IOStreamedResponse> send(http_api.BaseRequest request) async {
    final id = ++serial;
    final started = clock.elapsedMicroseconds;
    try {
      final response = await super.send(request);
      trace.writeln(jsonEncode({'type':'http', 'serial':id,
        'start_us':started,'headers_us':clock.elapsedMicroseconds,
        'path':request.url.path,'method':request.method,
        'status':response.statusCode,'content_length':response.contentLength}));
      return response;
    } catch(error) {
      trace.writeln(jsonEncode({'type':'http_error','serial':id,
        'start_us':started,'end_us':clock.elapsedMicroseconds,
        'path':request.url.path,'error':error.toString()}));
      rethrow;
    }
  }
}""",
)
source = source.replace(
    "final faults = <String, int>{};",
    r"""final faults = <String, int>{};
      final investigationClock = Stopwatch()..start();
      final trace = File('${out.path}/client-timeline.jsonl').openWrite();
      int inserted = 0, progress = 0, batchInserted = 0, batchProgress = 0;
      int? firstInsertUs, firstProgressUs, beforeCommitUs;
      void fault(String p) {
        faults.update(p, (n) => n + 1, ifAbsent: () => 1);
        final now=investigationClock.elapsedMicroseconds;
        if(p=='before_object_insert') { firstInsertUs ??= now; batchInserted++; }
        if(p=='after_object_insert') inserted++;
        if(p=='after_progress_insert') {firstProgressUs ??= now; batchProgress++; progress++;}
        if(p=='before_commit') beforeCommitUs=now;
        if(p=='after_commit') {
          trace.writeln(jsonEncode({'type':'commit','end_us':now,
            'first_insert_us':firstInsertUs,'first_progress_us':firstProgressUs,
            'before_commit_us':beforeCommitUs, 'batch_new':batchInserted,
            'batch_progress':batchProgress,'inserted':inserted,'progress':progress}));
          firstInsertUs=null; firstProgressUs=null; beforeCommitUs=null;
          batchInserted=0; batchProgress=0;
        }
      }""",
)
source = source.replace(
    "fault: (p) => faults.update(p, (n) => n + 1, ifAbsent: () => 1),", "fault: fault,"
)
source = source.replace(
    "final http = IOClient(native);",
    "final http = _MeterIOClient(native, trace, investigationClock);",
)
source = source.replace(
    "final result = <String, dynamic>{",
    r"""final snapshotTimer = Timer.periodic(const Duration(seconds: 30), (_) {
        final timing=Stopwatch()..start();
        final direct=sqlite3.open(store.path,mode:OpenMode.readOnly);
        try {
          trace.writeln(jsonEncode({'type':'snapshot','at_us':investigationClock.elapsedMicroseconds,
            'usage':Map<String,dynamic>.from(direct.select('SELECT * FROM usage').single),
            'acquisitions':direct.select('SELECT state,error_code FROM acquisition').map((r)=>Map<String,dynamic>.from(r)).toList(),
            'store_work':store.work.snapshot(), 'rss':ProcessInfo.currentRss,
            'database_bytes':File(store.path).lengthSync(),
            'wal_bytes':File('${store.path}-wal').existsSync()?File('${store.path}-wal').lengthSync():0,
            'probe_us':timing.elapsedMicroseconds}));
        } finally { direct.close(); }
        trace.flush();
      });
      final result = <String, dynamic>{""",
)
source = source.replace(
    "sampler.cancel();", "sampler.cancel();\n        snapshotTimer.cancel();"
)
source = source.replace(
    "result['e1_database_bytes'] = File(store.path).lengthSync();",
    "result['e1_database_bytes'] = File(store.path).lengthSync();\n        await trace.flush();\n        await trace.close();",
)
source = source.replace(
    "'B02 real cold D→E, original AppState ticket and closed R1 gate'",
    "'B02-A01 controlled real N50k cold investigation; limits unchanged'",
)
# Final investigation logger: preserve IO response semantics, avoid concurrent
# IOSink.flush()/write binding. Historical first source is separately retained.
source = source.replace("final IOSink trace;", "final _Trace trace;")
source = source.replace(
    "class _RealLoopback extends HttpOverrides {}",
    r"""class _RealLoopback extends HttpOverrides {}
class _Trace {
  _Trace(this.file);
  final File file;
  void writeln(Object? value) => file.writeAsStringSync('$value\n', mode:FileMode.append);
  Future<void> flush() async {}
  Future<void> close() async {}
}""",
)
source = source.replace(
    "final trace = File('${out.path}/client-timeline.jsonl').openWrite();",
    "final trace = _Trace(File('${out.path}/client-timeline.jsonl'));",
)
(HERE / "cold_test.dart").write_text(source)
print("조사 전용 클라이언트 생성; 기존 파일 변경 없음")
