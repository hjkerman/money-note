import 'package:intl/intl.dart';

final _wonFormat = NumberFormat.decimalPattern('ko_KR');

String won(num? value) => '${_wonFormat.format(value ?? 0)}원';

String shortDate(String? value) {
  if (value == null || value.length < 10) return '';
  return '${value.substring(5, 7)}/${value.substring(8, 10)}';
}
