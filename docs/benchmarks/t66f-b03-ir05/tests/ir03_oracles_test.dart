import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:sqlite3/sqlite3.dart';
import 'file:///tmp/money-note-ir05-20261024/candidate/mobile/test/support/logical_cost_sqlite.dart';

BigInt n(SqlCosts s,String k)=>s.values[k]??BigInt.zero;
void evidence(String name,Object value)=>File('/tmp/money-note-ir05-20261024/tests/$name.json').writeAsStringSync(jsonEncode(value));
void main(){
 for(final raw in [<int>[],utf8.encode('한😀e\u0301'),List<int>.generate(256,(i)=>i),List<int>.filled(65537,97)]){
  test('IR03 literal hash ${raw.length}',(){
   final preimage=[...ascii.encode('money-note.sync.v1/hot'),0,...raw],c=LogicalCost();
   final expected=sha256.convert(preimage).toString();
   c.run(LogicalCostStage.e2,(){expect(objectHash('hot',raw),expected);expect(objectHash('hot',raw),expected);});
   expect(c.snapshot()['e2/objectHash/hashInputBytes'],'${preimage.length*2}');
   final before=c.snapshot();c.close();c.run(LogicalCostStage.e4Read,()=>localChecksum(raw));expect(c.snapshot(),before);
  });
 }
 for(final v in [('{}',true),('{"x":"한😀"}',true),('{ }',false),('{"a":',false),('{"a":1,"a":2}',false),('"\\ud800"',false)]){
  test('IR03 primary C1 ${v.$1}',(){
   final raw=utf8.encode(v.$1),c=LogicalCost();c.run(LogicalCostStage.e3Verify,(){for(var i=0;i<3;i++){if(v.$2){decodeC1(raw);}else{expect(()=>decodeC1(raw),throwsA(isA<SegmentedException>()));}}});
   expect(c.snapshot()['e3Verify/c1/submittedBytes'],'${raw.length*3}');
   expect(c.snapshot()['e3Verify/c1/${v.$2?'completedBytes':'failedSubmittedBytes'}'],'${raw.length*3}');
  });
 }
 for(final mode in ['savepoint','fail','comment']){
  test('IR03 IA01-03 native closure $mode',(){
   final c=LogicalCost(),s=SqlCosts(),native=sqlite3.openInMemory(),d=CostDatabase(native,s);
   try{
    d.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
    c.run(LogicalCostStage.e1,(){
     if(mode=='savepoint'){
      for(final sql in ['BEGIN','SAVEPOINT s',"INSERT INTO payload VALUES('a',x'01')",'SAVEPOINT s',"INSERT INTO payload VALUES('b',x'0203')",'ROLLBACK TO s','RELEASE s','COMMIT']){d.execute(sql);}
     }else if(mode=='fail'){
      d.execute('BEGIN');d.execute("INSERT INTO payload VALUES('prior',x'01')");expect(()=>d.execute("INSERT OR FAIL INTO payload VALUES('a',x'0203'),('prior',x'040506')"),throwsA(isA<SqliteException>()));d.execute('COMMIT');
     }else{d.execute("/* independent */ INSERT INTO payload VALUES('a',x'0102')");}
    });
    final expected=native.select('SELECT sum(length(b)) n FROM payload').single['n'] as int;
    expect(expected,mode=='savepoint'?1:mode=='fail'?3:2);
    expect(n(s,'e1/payload/INSERT/blobBytes/committed'),BigInt.from(expected));
    if(mode=='savepoint'){expect(n(s,'e1/payload/INSERT/blobBytes/rolledBack'),BigInt.two);}
    evidence('dart-ia-$mode',{'expected':expected,'sqlite':s.snapshot()});
   }finally{d.close();}
  });
 }
 test('IR03 async closed scopes and original stage isolation',()async{
  final a=LogicalCost(),b=LogicalCost(),entered=Completer<void>(),resume=Completer<void>();
  final task=a.run(LogicalCostStage.e2,()async{localChecksum([1,2,3]);entered.complete();await resume.future;localChecksum(List.filled(91,1));throw StateError('late');});
  final failure=expectLater(task,throwsStateError);await entered.future;a.close();final before=a.snapshot();
  await b.run(LogicalCostStage.e3Verify,()async{localChecksum(List.filled(11,1));resume.complete();await failure;b.run(LogicalCostStage.e4Read,()=>localChecksum([1]));});
  expect(a.snapshot(),before);expect(b.snapshot()['e3Verify/checksum/hashInputBytes'],'11');expect(b.snapshot()['e4Read/checksum/hashInputBytes'],'1');expect(LogicalCost.activeCollector,isNull);
 });
 test('IR03 cache32 exact binds, eviction, connection isolation, close',(){
  final a=CostDatabase(sqlite3.openInMemory(),SqlCosts()),b=CostDatabase(sqlite3.openInMemory(),SqlCosts());
  try{
   for(var i=0;i<80;i++){expect(a.select('SELECT ? v /* $i */',[i]).single['v'],i);}
   expect(a.statementReuse['peakLive'],32);expect(a.statementReuse['evictions'],48);
   for(var i=0;i<30;i++){
    expect(a.select('SELECT ? v',[i.isEven?[1,2,3]:null]).single['v'],i.isEven?[1,2,3]:null);
    expect(b.select('SELECT ? v',[i]).single['v'],i);
   }
  }finally{a.close();b.close();}
  expect(a.statementReuse['created'],a.statementReuse['finalized']);expect(b.statementReuse['created'],b.statementReuse['finalized']);expect(()=>a.select('SELECT 1'),throwsStateError);
 });
 for(final op in ['alter','drop_recreate']){
  test('IR03 DDL observer $op',(){
   final c=LogicalCost(),s=SqlCosts(),native=sqlite3.openInMemory(),d=CostDatabase(native,s);
   try{
    d.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
    c.run(LogicalCostStage.e1,(){
     d.execute("INSERT INTO payload VALUES('initial',x'01')");
     if(op=='alter'){d.execute('ALTER TABLE payload ADD COLUMN extra BLOB');d.execute("INSERT INTO payload VALUES('next',x'0203',x'040506')");}
     else{d.execute('DROP TABLE payload');d.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');d.execute("INSERT INTO payload VALUES('next',x'020304')");}
    });
    final expected=op=='alter'?6:4;
    final oracle=op=='alter'?native.select('SELECT sum(length(b))+sum(COALESCE(length(extra),0)) n FROM payload').single['n']:1+(native.select('SELECT sum(length(b)) n FROM payload').single['n'] as int);
    final actual=n(s,'e1/payload/INSERT/blobBytes/committed');
    evidence('dart-new-ddl-$op',{'expected':expected,'native':oracle,'actual':actual.toString(),'sqlite':s.snapshot()});
    expect(oracle,expected);expect(actual,BigInt.from(expected));
   }finally{d.close();}
  });
 }
}
