import 'dart:io';

Future<void> main() async {
  final dir = Directory.systemTemp.createTempSync('mn-a01-sink-');
  final file = File('${dir.path}/trace');
  final sink = file.openWrite();
  sink.writeln('before');
  final flushing = sink.flush();
  try {
    sink.writeln('during');
    stdout.writeln('WRITE_DURING_FLUSH=SUCCESS');
  } catch (error) {
    stdout.writeln('WRITE_DURING_FLUSH=${error.runtimeType}: $error');
  }
  await flushing;
  sink.writeln('after');
  await sink.close();
}
