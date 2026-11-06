import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:sqlite3/sqlite3.dart';
import 'file:///tmp/money-note-ir04-20261024/candidate/mobile/test/support/logical_cost_sqlite.dart';
BigInt value(SqlCosts s,String t,String op,String phase,[String metric='blobBytes'])=>s.values['e1/$t/$op/$metric/$phase']??BigInt.zero;
void record(String name,Object v)=>File('/tmp/money-note-ir04-20261024/evidence/$name.json').writeAsStringSync(jsonEncode(v));
void main(){
 for(final outcome in ['commit','rollback','savepoint']){
  test('IR04 independent schema literal ledger $outcome',(){
   final states=<String>[];
   for(final enabled in [false,true]){
    final raw=sqlite3.openInMemory(),s=SqlCosts(),c=LogicalCost();final Database d=enabled?CostDatabase(raw,s):raw;
    try{
     d.execute('CREATE TABLE p(id INTEGER PRIMARY KEY,b BLOB)');
     c.run(LogicalCostStage.e1,(){
      d.execute('INSERT INTO p VALUES(?,?)',[1,[1]]);d.execute('BEGIN');if(outcome=='savepoint')d.execute('SAVEPOINT x');
      d.execute("ALTER TABLE p ADD COLUMN t TEXT DEFAULT '한'");d.execute('INSERT INTO p(id,b) VALUES(?,?)',[2,[2,3]]);d.execute('UPDATE p SET b=? WHERE id=2',[[4,5,6,7]]);
      d.execute('INSERT INTO p VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET b=excluded.b,t=excluded.t',[2,[8,9,0],'😀']);d.execute('DELETE FROM p WHERE id=2');
      d.execute('CREATE TABLE q(b BLOB)');d.execute('INSERT INTO q VALUES(?)',[[1,2,3,4,5]]);
      if(outcome=='savepoint'){d.execute('ROLLBACK TO x');d.execute('RELEASE x');d.execute('INSERT INTO p VALUES(?,?)',[3,[1,2,3,4,5,6]]);d.execute('COMMIT');}else{d.execute(outcome=='commit'?'COMMIT':'ROLLBACK');}
     });
     final tables=raw.select("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").map((r)=>r['name']).toList();
     final state={'tables':tables,'p':raw.select('SELECT * FROM p').map((r)=>r.values.toList()).toList(),'q':tables.contains('q')?raw.select('SELECT * FROM q').map((r)=>r.values.toList()).toList():null};states.add(jsonEncode(state));
     if(enabled){
      final extra=outcome=='savepoint'?6:0;
      expect(value(s,'p','INSERT','attempted'),BigInt.from(6+extra));expect(value(s,'p','INSERT','effective'),BigInt.from(3+extra));expect(value(s,'p','INSERT','committed'),BigInt.from(outcome=='commit'?3:1+extra));
      expect(value(s,'p','INSERT','attempted','textBytes'),BigInt.from(7));expect(value(s,'p','INSERT','effective','textBytes'),BigInt.from(3));
      expect(value(s,'p','UPDATE','attempted'),BigInt.from(7));expect(value(s,'p','UPDATE','effective'),BigInt.from(7));expect(value(s,'p','UPDATE','committed'),BigInt.from(outcome=='commit'?7:0));
      expect(value(s,'p','UPDATE','attempted','textBytes'),BigInt.from(7));expect(value(s,'p','UPDATE','effective','textBytes'),BigInt.from(7));
      expect(value(s,'q','INSERT','attempted'),BigInt.from(5));expect(value(s,'q','INSERT','effective'),BigInt.from(5));expect(value(s,'q','INSERT','committed'),BigInt.from(outcome=='commit'?5:0));
      expect(value(s,'p','DELETE','effective'),BigInt.zero);expect(s.values['e1/p/DELETE/effective/rows'],BigInt.one);
      if(outcome!='commit'){expect(value(s,'p','INSERT','rolledBack'),BigInt.two);expect(value(s,'p','UPDATE','rolledBack'),BigInt.from(7));expect(value(s,'q','INSERT','rolledBack'),BigInt.from(5));}
      record('dart-schema-ledger-$outcome',{'state':state,'counters':s.snapshot()});
     }
    }finally{d.close();}
   }
   expect(states[0],states[1]);
  });
 }
 test('IR04 same managed statement reprepare literal 1+5+2',(){
  final s=SqlCosts(),c=LogicalCost(),raw=sqlite3.openInMemory();final d=CostDatabase(raw,s);const sql='INSERT INTO p(b) VALUES(?)';
  try{
   d.execute('CREATE TABLE p(b BLOB)');
   c.run(LogicalCostStage.e1,(){d.execute(sql,[[1]]);d.execute("ALTER TABLE p ADD COLUMN extra BLOB DEFAULT x'0102'");d.execute(sql,[[1,2,3]]);d.execute('DROP TABLE p');d.execute('CREATE TABLE p(b BLOB)');d.execute(sql,[[1,2]]);});
   for(final phase in ['attempted','effective','committed']){expect(value(s,'p','INSERT',phase),BigInt.from(8));}
   expect(raw.select('SELECT b FROM p').single['b'],[1,2]);expect(d.statementReuse['hits'],2);record('dart-schema-cached',{'literal_ledger':[1,5,2],'counters':s.snapshot(),'cache':d.statementReuse});
  }finally{d.close();}
  expect(d.statementReuse['created'],d.statementReuse['finalized']);
 });
 for(final replace in [false,true]){
  test('IR04 external DDL rejects before write replace=$replace',(){
   final temp=Directory.systemTemp.createTempSync('ir04-external-');final path='${temp.path}/audit.sqlite';final s=SqlCosts(),c=LogicalCost(),raw=sqlite3.open(path),other=sqlite3.open(path);final d=CostDatabase(raw,s);
   try{
    d.execute('CREATE TABLE p(b BLOB)');c.run(LogicalCostStage.e1,()=>d.execute("INSERT INTO p VALUES(x'01')"));
    if(replace){other.execute('DROP TABLE p');other.execute('CREATE TABLE p(b BLOB)');}else{other.execute('ALTER TABLE p ADD COLUMN extra BLOB');}
    final before=jsonEncode(other.select('SELECT * FROM p').map((r)=>r.values.toList()).toList());
    c.run(LogicalCostStage.e1,(){for(var i=0;i<2;i++){expect(()=>d.execute('INSERT INTO p(b) VALUES(?)',[[1,2,3]]),throwsA(isA<StateError>().having((e)=>e.message,'message',contains('external schema change; measurement incomplete'))));}});
    expect(jsonEncode(other.select('SELECT * FROM p').map((r)=>r.values.toList()).toList()),before);
    for(final phase in ['attempted','effective','committed']){expect(value(s,'p','INSERT',phase),BigInt.one);}
    expect(s.values['e1/coverage/externalSchemaChange'],BigInt.two);record('dart-schema-external-$replace',{'state':before,'counters':s.snapshot(),'rejected_before_new_row':true,'measurement_incomplete':true});
   }finally{d.close();other.close();temp.deleteSync(recursive:true);}
  });
 }
}
