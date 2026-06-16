import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

const _tokenKey = 'money_note_session_token';

class MoneyNoteApiClient {
  MoneyNoteApiClient({
    http.Client? client,
    String? baseUrl,
  })  : _client = client ?? http.Client(),
        baseUrl = baseUrl ??
            const String.fromEnvironment('MONEY_NOTE_API_BASE_URL',
                defaultValue: 'http://10.0.2.2:18080');

  final http.Client _client;
  final String baseUrl;

  Uri sharePageUri(String panelType) => _uri('/share/$panelType');

  String? _sessionToken;

  Future<void> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    _sessionToken = prefs.getString(_tokenKey);
  }

  Future<void> saveSession(String? token) async {
    _sessionToken = token;
    final prefs = await SharedPreferences.getInstance();
    if (token == null || token.isEmpty) {
      await prefs.remove(_tokenKey);
      return;
    }
    await prefs.setString(_tokenKey, token);
  }

  Future<AuthUser> login(String username, String password) async {
    final user = await _post(
      '/api/auth/mobile-login',
      {'username': username, 'password': password},
      AuthUser.fromJson,
    );
    await saveSession(user.sessionToken);
    return user;
  }

  Future<void> logout() async {
    try {
      await _post('/api/auth/logout', const {}, (json) => json);
    } finally {
      await saveSession(null);
    }
  }

  Future<AuthUser> me() => _get('/api/auth/me', AuthUser.fromJson);

  Future<void> health() async {
    final response = await _client.get(_uri('/health'));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw MoneyNoteApiException('서버 상태 확인에 실패했습니다.');
    }
  }

  Future<Summary> summary() =>
      _get('/api/month/current/summary', Summary.fromJson);

  Future<JudgmentState> judgment() =>
      _get('/api/judgment/current', JudgmentState.fromJson);

  Future<List<LedgerEntry>> currentEntries() {
    return _getList('/api/entries/current', LedgerEntry.fromJson);
  }

  Future<List<MonthlyPanel>> currentPanels() {
    return _getList('/api/month/current/panels', MonthlyPanel.fromJson);
  }

  Future<List<CashFlow>> cashFlows() {
    return _getList('/api/cash-flows', CashFlow.fromJson);
  }

  Future<AppSettings> settings() {
    return _get('/api/settings', AppSettings.fromJson);
  }

  Future<AppSettings> updateSetting(String key, String value) {
    return _patch('/api/settings/$key', {'value': value}, AppSettings.fromJson);
  }

  Future<CardDiscountMonth> discountMonth(String month, String scope) {
    return _get('/api/card-discounts/months/$month?scope=$scope',
        CardDiscountMonth.fromJson);
  }

  Future<MonthCloseStatus> monthCloseStatus() {
    return _get('/api/month/current/status', MonthCloseStatus.fromJson);
  }

  Future<LedgerEntry> createExpense({
    required String date,
    required String usagePlace,
    required String usageItem,
    required int amount,
    String? spendingCategory,
  }) {
    return _post(
        '/api/entries',
        {
          'book_section': 'current',
          'entry_kind': 'expense',
          'entry_date': date,
          'date_label': null,
          'group_label': null,
          'title': usageItem.trim().isEmpty
              ? usagePlace.trim()
              : '[${usagePlace.trim()}] ${usageItem.trim()}',
          'usage_place': usagePlace.trim(),
          'usage_item': usageItem.trim().isEmpty ? null : usageItem.trim(),
          'amount_value': amount,
          'amount_expr': null,
          'aux_amount_value': null,
          'aux_amount_expr': null,
          'extra_value': null,
          'sort_order': 0,
          'due_day': null,
          'confirmed_at': null,
          'spending_category': spendingCategory,
        },
        LedgerEntry.fromJson);
  }

  Future<LedgerEntry> updateEntryCategory(int entryId, String? category) {
    return _patch('/api/entries/$entryId', {'spending_category': category},
        LedgerEntry.fromJson);
  }

  Future<void> deleteEntry(int entryId) async {
    await _delete('/api/entries/$entryId');
  }

  Future<LedgerEntry> createPlannedEntry({
    required int dueDay,
    required String usagePlace,
    required String usageItem,
    required int amount,
  }) {
    final trimmedPlace = usagePlace.trim();
    final trimmedItem = usageItem.trim();
    return _post(
        '/api/month/current/planned',
        {
          'title': trimmedItem.isEmpty
              ? trimmedPlace
              : '[$trimmedPlace] $trimmedItem',
          'usage_place': trimmedPlace,
          'usage_item': trimmedItem.isEmpty ? null : trimmedItem,
          'amount_value': amount,
          'amount_expr': null,
          'due_day': dueDay,
        },
        LedgerEntry.fromJson);
  }

  Future<Map<String, dynamic>> confirmPlannedEntry(int entryId) {
    return _post('/api/month/current/planned/$entryId/confirm', const {},
        (json) => json);
  }

  Future<void> deletePlannedEntry(int entryId) async {
    await _delete('/api/month/current/planned/$entryId');
  }

  Future<LedgerEntry> excludeEntryDiscount(String entryPaymentKey) {
    return _patch('/api/card-discounts/entries/$entryPaymentKey',
        {'discount_amount': 0}, LedgerEntry.fromJson);
  }

  Future<void> clearEntryDiscount(String entryPaymentKey) async {
    await _delete('/api/card-discounts/entries/$entryPaymentKey');
  }

  Future<MonthlyPanel> createPanel({
    required String month,
    required String panelType,
    required String title,
    required int amount,
    String? spentOn,
  }) {
    return _post(
        '/api/month/current/panels',
        {
          'month': month,
          'panel_type': panelType,
          'title': title.trim(),
          'spent_on': spentOn,
          'amount_value': amount,
          'discount_amount': 0,
          'discount_override': 0,
          'amount_expr': null,
          'sort_order': 0,
          'due_day': null,
          'confirmed_at': null,
        },
        MonthlyPanel.fromJson);
  }

  Future<MonthlyPanel> excludePanelDiscount(int panelId) {
    return _patch('/api/month/current/panels/$panelId/discount',
        {'discount_amount': 0}, MonthlyPanel.fromJson);
  }

  Future<void> clearPanelDiscount(int panelId) async {
    await _delete('/api/month/current/panels/$panelId/discount');
  }

  Future<Map<String, dynamic>> completePanelType(String panelType) {
    return _post('/api/month/current/panels/type/$panelType/complete', const {},
        (json) => json);
  }

  Future<void> deletePanel(int panelId) async {
    await _delete('/api/month/current/panels/$panelId');
  }

  Future<CashFlow> createCashFlow({
    required String occurredOn,
    required String title,
    required int amount,
    required bool isPrimaryIncome,
  }) {
    return _post(
      '/api/cash-flows',
      {
        'occurred_on': occurredOn,
        'title': title.trim(),
        'amount_value': amount,
        'sort_order': 0,
        'is_primary_income': isPrimaryIncome ? 1 : 0,
      },
      CashFlow.fromJson,
    );
  }

  Future<void> deleteCashFlow(int flowId) async {
    await _delete('/api/cash-flows/$flowId');
  }

  Future<SnapshotDownload> downloadSnapshot() async {
    final response =
        await _client.get(_uri('/api/admin/snapshot'), headers: _headers());
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw MoneyNoteApiException(_readError(response));
    }
    return SnapshotDownload(
      filename:
          _readDownloadFilename(response.headers['content-disposition']) ??
              'money-note-snapshot.money-note-snapshot.json',
      bytes: response.bodyBytes,
    );
  }

  Future<Map<String, dynamic>> closeCurrentMonth(
      {bool allowEarlyClose = false}) {
    return _post('/api/month/current/close',
        {'allow_early_close': allowEarlyClose}, (json) => json);
  }

  Future<Map<String, dynamic>> restoreSnapshot({
    required String password,
    required String snapshotText,
  }) {
    return _post('/api/admin/snapshot/restore',
        {'password': password, 'snapshot_text': snapshotText}, (json) => json);
  }

  Future<T> _get<T>(
      String path, T Function(Map<String, dynamic>) parser) async {
    final response = await _client.get(_uri(path), headers: _headers());
    return parser(_parseMap(response));
  }

  Future<List<T>> _getList<T>(
      String path, T Function(Map<String, dynamic>) parser) async {
    final response = await _client.get(_uri(path), headers: _headers());
    final decoded = _parseJson(response);
    if (decoded is! List) throw MoneyNoteApiException('응답 형식이 올바르지 않습니다.');
    return decoded.map((item) => parser(item as Map<String, dynamic>)).toList();
  }

  Future<T> _post<T>(String path, Map<String, dynamic> body,
      T Function(Map<String, dynamic>) parser) async {
    final response = await _client.post(
      _uri(path),
      headers: {'Content-Type': 'application/json', ..._headers()},
      body: jsonEncode(body),
    );
    return parser(_parseMap(response));
  }

  Future<T> _patch<T>(String path, Map<String, dynamic> body,
      T Function(Map<String, dynamic>) parser) async {
    final response = await _client.patch(
      _uri(path),
      headers: {'Content-Type': 'application/json', ..._headers()},
      body: jsonEncode(body),
    );
    return parser(_parseMap(response));
  }

  Future<void> _delete(String path) async {
    final response = await _client.delete(_uri(path), headers: _headers());
    _parseJson(response);
  }

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Map<String, String> _headers() {
    final token = _sessionToken;
    return token == null || token.isEmpty
        ? const {}
        : {'Authorization': 'Bearer $token'};
  }

  Map<String, dynamic> _parseMap(http.Response response) {
    final decoded = _parseJson(response);
    if (decoded is! Map<String, dynamic>) {
      throw MoneyNoteApiException('응답 형식이 올바르지 않습니다.');
    }
    return decoded;
  }

  dynamic _parseJson(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw MoneyNoteApiException(_readError(response));
    }
    if (response.body.isEmpty) return <String, dynamic>{};
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  String _readError(http.Response response) {
    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (decoded is Map && decoded['detail'] is String) {
        if (decoded['detail'] == 'invalid username or password') {
          return '아이디 또는 비밀번호가 맞지 않습니다.';
        }
        if (decoded['detail'] == 'authentication required') {
          return '로그인이 필요합니다.';
        }
        return decoded['detail'] as String;
      }
    } catch (_) {
      // 서버가 JSON이 아닌 오류를 줄 때도 사용자에게는 짧게 보여준다.
    }
    return '서버 요청에 실패했습니다. (${response.statusCode})';
  }

  String? _readDownloadFilename(String? header) {
    if (header == null || header.isEmpty) return null;
    final utf8Match = RegExp(r"filename\\*=UTF-8''([^;]+)").firstMatch(header);
    if (utf8Match != null) return Uri.decodeComponent(utf8Match.group(1)!);
    final quotedMatch = RegExp(r'filename="([^"]+)"').firstMatch(header);
    if (quotedMatch != null) return quotedMatch.group(1);
    return null;
  }
}

class MoneyNoteApiException implements Exception {
  MoneyNoteApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class SnapshotDownload {
  SnapshotDownload({required this.filename, required this.bytes});

  final String filename;
  final Uint8List bytes;
}
