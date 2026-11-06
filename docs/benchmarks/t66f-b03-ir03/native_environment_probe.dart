import 'package:sqlite3/sqlite3.dart';
void main(){ final database=sqlite3.openInMemory();try{if(database.select('SELECT 1 AS v').single['v']!=1){throw StateError('native oracle');}}finally{database.close();}}
