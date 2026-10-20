import 'dart:convert';
import 'dart:io';

import 'package:sqlite3/sqlite3.dart';

void main() {
  stdout.writeln(
    jsonEncode({
      'dart': Platform.version,
      'client_sqlite': sqlite3.version.libVersion,
      'client_sqlite_source': sqlite3.version.sourceId,
    }),
  );
}
