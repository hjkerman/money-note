@Timeout(Duration(minutes:8))
library;
import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:sqlite3/sqlite3.dart';
import 'file:///tmp/money-note-ir04-20261024/tests/integration_original_test.dart' as native;
import 'file:///tmp/money-note-ir04-20261024/candidate/docs/benchmarks/t66f-phase-b/harness.dart';
import 'file:///tmp/money-note-ir04-20261024/candidate/mobile/test/support/logical_cost_sqlite.dart';

void main(){
 TestWidgetsFlutterBinding.ensureInitialized();
 test('IR03 actual TLS cold identical card cash OFF ON canonical durable oracle',()async{
  final backend=await native.start();
  final off=await RealHarness.create(RealBackend.remote(backend.initial));
  final on=await RealHarness.create(RealBackend.remote(backend.initial));
  final c=LogicalCost(),sql=SqlCosts(),cache=on.store.cache;on.store.close();
  on.store=SegmentedClientStore.open(on.root,cache,adapters:true,diagnosticDatabaseFactory:(p)=>CostDatabase(sqlite3.open(p),sql));
  final phases=<String,Object?>{};
  try{
   var previousRoot='';var previousNewBytes=BigInt.zero;
   for(final phase in ['cold','identical','card','cash']){
    if(phase=='card'||phase=='cash'){await backend.command({'command':'mutate','op':phase=='card'?'update':'cash'});}
    final a=await off.state.publishSegmentedForIsolatedUse(off.store);
    final b=await c.run(LogicalCostStage.e2,()=>on.state.publishSegmentedForIsolatedUse(on.store));
    final expected=await backend.command({'command':'oracle'});
    final target=expected['manifest']['target'];
    expect(a.sequence,b.sequence);expect(b.sequence,phase=='cold'||phase=='identical'?1:phase=='card'?2:3);
    final roots=<String>[];
    for(final h in [off,on]){
     final accepted=h.store.acceptedGeneration();final root=accepted.manifest!.target.syncRoot;roots.add(root);expect(root,target['sync_root']);
     final database=sqlite3.open(h.store.path);
     try{
      for(final object in expected['objects']){
       final raw=base64Decode(object['data_base64']);final kind=(jsonDecode(utf8.decode(raw)) as Map)['kind'];
       final digest=sha256.convert([...ascii.encode('money-note.sync.v1/$kind'),0,...raw]).toString();expect(digest,object['ref']['hash']);
       expect(database.select('SELECT body FROM objects WHERE hash=?',[digest]).single['body'],raw);
      }
      expect(database.select('PRAGMA foreign_key_check'),isEmpty);
      expect(database.select('SELECT sequence FROM accepted').single['sequence'],b.sequence);
      if(identical(h,on)){
       final total=database.select('SELECT sum(length(body)) n FROM objects').single['n'] as int;
       expect(sql.values['e2/objects/INSERT/blobBytes/committed'],BigInt.from(total));
       if(phase=='identical'){expect(BigInt.from(total),previousNewBytes);expect(root,previousRoot);}
       previousNewBytes=BigInt.from(total);previousRoot=root;
      }
     }finally{database.close();}
     c.run(LogicalCostStage.e4Read,()=>h.store.withAcceptedRead(accepted,(r){
      for(final entry in (expected['source'] as Map).entries){expect(r.rows(entry.key as String,limit:256),unorderedEquals(entry.value as List));}
      expect(r.hot['state'],expected['expected_hot']);
     }));
    }
    expect(roots[0],roots[1]);final measured=await backend.command({'command':'cost'});native.verifyNativeWitness(measured);
    phases[phase]={'oracle':expected,'root':roots[0],'sequence':b.sequence,'expected_objects':(expected['objects'] as List).length,'committed_object_bytes':previousNewBytes.toString(),'primitive':c.snapshot(),'sql':sql.snapshot()};
   }
   await backend.command({'command':'mutate','op':'update','title':'IR03 rejected-object'});
   final failures=<String>[];
   for(final h in [off,on]){
    final prior=h.store.acceptedGeneration();
    await backend.command({'command':'fault','mode':'bad_object','path':'/objects'});
    AcquisitionFailure? error;
    try{
     if(identical(h,on)){await c.run(LogicalCostStage.e2,()=>h.state.publishSegmentedForIsolatedUse(h.store));}
     else{await h.state.publishSegmentedForIsolatedUse(h.store);}
    }on AcquisitionFailure catch(e){error=e;}
    expect(error,isNotNull,reason:'실제 손상 객체는 accepted로 게시될 수 없음');
    expect(error!.action,'blocked');failures.add(error.code);
    final after=h.store.acceptedGeneration();expect(after.id,prior.id);expect(after.sequence,3);expect(after.manifest!.target.syncRoot,previousRoot);
   }
   expect(failures[0],failures[1]);phases['rejected']={'same_error':failures[0],'accepted_sequence':3,'preserved':true,'source_oracle':await backend.command({'command':'oracle'}),'wire':await backend.command({'command':'stats'})};
   expect(LogicalCost.activeCollector,isNull);final before=c.snapshot();c.close();c.run(LogicalCostStage.e2,()=>on.store.acceptedGeneration());expect(c.snapshot(),before);
   File('/tmp/money-note-ir04-20261024/tests/delta-integration.json').writeAsStringSync(jsonEncode({'phases':phases,'equivalent':true,'counter_closed':true}));
  }finally{off.dispose();on.dispose();await backend.close();}
 });
}
