import 'dart:convert';
import 'dart:io';
import 'package:sqlite3/sqlite3.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'file:///tmp/money-note-ir03-20261023/candidate/mobile/test/support/logical_cost_sqlite.dart';
void main(){
 final results=<Object>[];
 for(final op in ['alter','drop_recreate']){
  final c=LogicalCost(),sql=SqlCosts(),native=sqlite3.openInMemory(),d=CostDatabase(native,sql);
  try{
   d.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
   c.run(LogicalCostStage.e1,(){
    d.execute("INSERT INTO payload VALUES('initial',x'01')");
    if(op=='alter'){d.execute('ALTER TABLE payload ADD COLUMN extra BLOB');d.execute("INSERT INTO payload VALUES('next',x'0203',x'040506')");}
    else{d.execute('DROP TABLE payload');d.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');d.execute("INSERT INTO payload VALUES('next',x'020304')");}
   });
   final actual=sql.values['e1/payload/INSERT/blobBytes/committed'].toString();
   final expected=op=='alter'?6:4;
   final nativeBytes=op=='alter'?native.select('SELECT sum(length(b))+sum(COALESCE(length(extra),0)) n FROM payload').single['n']:1+(native.select('SELECT sum(length(b)) n FROM payload').single['n'] as int);
   results.add({'mode':op,'expected':expected,'native':nativeBytes,'actual':actual,'counters':sql.snapshot()});
  }finally{d.close();}
 }
 File('/tmp/money-note-ir03-20261023/evidence/dart-ddl-native.json').writeAsStringSync(jsonEncode(results));
 print(jsonEncode(results));
 exitCode=results.cast<Map>().every((x)=>x['expected'].toString()==x['actual'])?0:1;
}
