import 'package:flutter/services.dart';

import 'api_client.dart';
import 'formatters.dart';
import 'models.dart';

const auditInstructionsAssetPath = 'assets/ai_audit_instructions.md';

Future<String> loadAuditInstructions({AssetBundle? assetBundle}) async {
  final instructions = await (assetBundle ?? rootBundle).loadString(
    auditInstructionsAssetPath,
  );
  if (instructions.trim().isEmpty) {
    throw const FormatException('회계감사 지침 파일이 비어 있습니다.');
  }
  return instructions;
}

class AiAuditReportData {
  AiAuditReportData({
    required this.latestAllowedMonth,
    required this.ledgerEntries,
    required this.cashFlows,
    required this.panels,
    required this.confirmedPlannedEntries,
    required this.auditInstructions,
  });

  final String latestAllowedMonth;
  final List<LedgerEntry> ledgerEntries;
  final List<CashFlow> cashFlows;
  final List<MonthlyPanel> panels;
  final List<LedgerEntry> confirmedPlannedEntries;
  final String auditInstructions;

  static Future<AiAuditReportData> load(
    MoneyNoteApiClient api, {
    required String latestAllowedMonth,
  }) async {
    final results = await Future.wait([
      api.currentEntries(),
      api.archiveEntries(),
      api.cashFlows(),
      api.currentPanels(),
      api.confirmedPlannedEntries(),
      loadAuditInstructions(),
    ]);
    return AiAuditReportData(
      latestAllowedMonth: latestAllowedMonth,
      ledgerEntries: [
        ...(results[0] as List<LedgerEntry>),
        ...(results[1] as List<LedgerEntry>),
      ],
      cashFlows: results[2] as List<CashFlow>,
      panels: results[3] as List<MonthlyPanel>,
      confirmedPlannedEntries: results[4] as List<LedgerEntry>,
      auditInstructions: results[5] as String,
    );
  }

  List<String> get availableMonths {
    final months = <String>{};
    for (final entry in ledgerEntries) {
      if (entry.entryKind == 'expense') {
        _addValidMonth(months, _monthOf(entry.entryDate));
      }
    }
    for (final flow in cashFlows) {
      _addValidMonth(months, _monthOf(flow.occurredOn));
    }
    for (final panel in panels) {
      if (panel.panelType == 'claim' || panel.panelType == 'family_card') {
        _addValidMonth(months, _panelMonth(panel));
      }
    }
    final sorted = months.toList()..sort((a, b) => b.compareTo(a));
    return sorted;
  }

  bool containsMonth(String month) => availableMonths.contains(month);

  String buildMarkdown(String month, {DateTime? generatedAt}) {
    if (!containsMonth(month)) {
      throw ArgumentError.value(month, 'month', '기록이 존재하는 연월이어야 합니다.');
    }
    final expenses = ledgerEntries
        .where((entry) =>
            entry.entryKind == 'expense' && _monthOf(entry.entryDate) == month)
        .toList()
      ..sort(_compareLedgerEntries);
    final monthCashFlows = cashFlows
        .where((flow) => _monthOf(flow.occurredOn) == month)
        .toList()
      ..sort(_compareCashFlows);
    final claims = panels
        .where((panel) =>
            panel.panelType == 'claim' && _panelMonth(panel) == month)
        .toList()
      ..sort(_comparePanels);
    final familyCards = panels
        .where((panel) =>
            panel.panelType == 'family_card' && _panelMonth(panel) == month)
        .toList()
      ..sort(_comparePanels);
    final fixedExpenses = panels
        .where((panel) => panel.panelType == 'fixed')
        .toList()
      ..sort(_compareFixedPanels);
    final frozenAmounts = panels
        .where((panel) => panel.panelType == 'frozen')
        .toList()
      ..sort(_comparePanels);
    final plannedById = <int, LedgerEntry>{
      for (final entry
          in ledgerEntries.where((entry) => entry.entryKind == 'planned'))
        entry.id: entry,
      for (final entry in confirmedPlannedEntries) entry.id: entry,
    };
    final plannedExpenses = plannedById.values.toList()
      ..sort(_comparePlannedEntries);
    final timestamp = (generatedAt ?? DateTime.now()).toIso8601String();

    return [
      '# Money-Note 회계감사 자료 - ${_monthLabel(month)}',
      '',
      '- 분석 대상: ${_monthLabel(month)}',
      '- 생성 시각: $timestamp',
      '- 통화 단위: 대한민국 원(KRW), 정수 금액',
      '',
      '## 회계감사 지침',
      '',
      auditInstructions.trim(),
      '',
      '## 본인 카드 지출',
      '',
      _expenseTable(expenses),
      '',
      '## 현금흐름',
      '',
      _cashFlowTable(monthCashFlows),
      '',
      '## 미정산 청구',
      '',
      '> 처리 완료된 청구는 Money-Note 운영 정책에 따라 삭제되므로 현재 남아 있는 미정산 항목만 표시됩니다.',
      '',
      _panelTable(claims, netLabel: '실청구액'),
      '',
      '## 미정산 가족카드',
      '',
      '> 처리 완료된 가족카드 내역은 Money-Note 운영 정책에 따라 삭제되므로 현재 남아 있는 미정산 항목만 표시됩니다.',
      '',
      _panelTable(familyCards, netLabel: '실결제액'),
      '',
      '## 현재 운영 참고자료',
      '',
      '> 아래 항목은 선택 월 당시의 이력이 아니라 보고서 생성 시점 현재 설정과 미삭제 목록입니다.',
      '',
      '### 현금성 고정지출',
      '',
      _fixedExpenseTable(fixedExpenses),
      '',
      '### 카드 정기결제',
      '',
      _plannedExpenseTable(plannedExpenses),
      '',
      '### 현재 동결 금액',
      '',
      '> 사용자가 해동하여 삭제한 과거 항목은 포함되지 않으며, 현재 남아 있는 동결 항목만 표시됩니다.',
      '',
      _frozenAmountTable(frozenAmounts),
      '',
    ].join('\n');
  }

  void _addValidMonth(Set<String> months, String? month) {
    if (month != null && month.compareTo(latestAllowedMonth) <= 0) {
      months.add(month);
    }
  }
}

String _fixedExpenseTable(List<MonthlyPanel> rows) {
  if (rows.isEmpty) return '_현재 설정된 현금성 고정지출 없음_';
  return _markdownTable(
    const ['내용', '월 예정금액'],
    rows.map((panel) => [panel.title, won(panel.amountValue ?? 0)]),
    numericColumns: const {1},
  );
}

String _plannedExpenseTable(List<LedgerEntry> rows) {
  if (rows.isEmpty) return '_현재 설정된 카드 정기결제 없음_';
  return _markdownTable(
    const ['결제일', '사용처', '세부내역', '월 예정금액'],
    rows.map((entry) => [
          entry.dueDay == null ? '' : '매월 ${entry.dueDay}일',
          entry.usagePlace ?? '',
          entry.usageItem ?? '',
          won(entry.amountValue ?? 0),
        ]),
    numericColumns: const {3},
  );
}

String _frozenAmountTable(List<MonthlyPanel> rows) {
  if (rows.isEmpty) return '_현재 남아 있는 동결 금액 없음_';
  return _markdownTable(
    const ['등록일', '내용', '금액'],
    rows.map((panel) => [
          panel.spentOn ?? '',
          panel.title,
          won(panel.amountValue ?? 0),
        ]),
    numericColumns: const {2},
  );
}

String _expenseTable(List<LedgerEntry> rows) {
  if (rows.isEmpty) return '_해당 내역 없음_';
  return _markdownTable(
    const ['사용일', '사용처', '세부내역', '분류', '사용금액', '할인액', '실결제액'],
    rows.map((entry) => [
          entry.entryDate ?? '',
          entry.usagePlace ?? '',
          entry.usageItem ?? '',
          spendingCategoryLabel(entry.spendingCategory),
          won(entry.amountValue),
          won(entry.effectiveDiscountAmount),
          won(entry.effectiveAmount),
        ]),
    numericColumns: const {4, 5, 6},
  );
}

String _cashFlowTable(List<CashFlow> rows) {
  if (rows.isEmpty) return '_해당 내역 없음_';
  return _markdownTable(
    const ['일자', '내용', '금액', '구분'],
    rows.map((flow) => [
          flow.occurredOn,
          flow.title,
          _signedWon(flow.amountValue),
          flow.isPrimaryIncome ? '주 수입' : '',
        ]),
    numericColumns: const {2},
  );
}

String _panelTable(List<MonthlyPanel> rows, {required String netLabel}) {
  if (rows.isEmpty) return '_해당 내역 없음_';
  return _markdownTable(
    ['사용일', '내용', '원금', '할인액', netLabel],
    rows.map((panel) => [
          panel.spentOn ?? '',
          panel.title,
          won(panel.amountValue),
          won(panel.effectiveDiscountAmount),
          won(panel.effectiveAmount),
        ]),
    numericColumns: const {2, 3, 4},
  );
}

String _markdownTable(
  List<String> headers,
  Iterable<List<Object?>> rows, {
  Set<int> numericColumns = const {},
}) {
  final alignment = List.generate(
    headers.length,
    (index) => numericColumns.contains(index) ? '---:' : '---',
  );
  return [
    '| ${headers.map(_markdownCell).join(' | ')} |',
    '| ${alignment.join(' | ')} |',
    ...rows.map((row) => '| ${row.map(_markdownCell).join(' | ')} |'),
  ].join('\n');
}

String _markdownCell(Object? value) {
  return (value ?? '')
      .toString()
      .replaceAll('\\', '\\\\')
      .replaceAll('|', '\\|')
      .replaceAll('\r', ' ')
      .replaceAll('\n', ' ')
      .trim();
}

String _signedWon(int value) {
  if (value > 0) return '+${won(value)}';
  if (value < 0) return '-${won(value.abs())}';
  return won(0);
}

String? _monthOf(String? value) {
  if (value == null || !RegExp(r'^\d{4}-\d{2}').hasMatch(value)) return null;
  final month = int.tryParse(value.substring(5, 7));
  if (month == null || month < 1 || month > 12) return null;
  return value.substring(0, 7);
}

String? _panelMonth(MonthlyPanel panel) {
  return _monthOf(panel.spentOn) ?? _monthOf(panel.month);
}

String _monthLabel(String month) {
  return '${month.substring(0, 4)}년 ${int.parse(month.substring(5, 7))}월';
}

int _compareLedgerEntries(LedgerEntry a, LedgerEntry b) {
  final dateCompare = (a.entryDate ?? '').compareTo(b.entryDate ?? '');
  if (dateCompare != 0) return dateCompare;
  final sortCompare = a.sortOrder.compareTo(b.sortOrder);
  if (sortCompare != 0) return sortCompare;
  return a.id.compareTo(b.id);
}

int _compareCashFlows(CashFlow a, CashFlow b) {
  final dateCompare = a.occurredOn.compareTo(b.occurredOn);
  if (dateCompare != 0) return dateCompare;
  final sortCompare = a.sortOrder.compareTo(b.sortOrder);
  if (sortCompare != 0) return sortCompare;
  return a.id.compareTo(b.id);
}

int _comparePanels(MonthlyPanel a, MonthlyPanel b) {
  final dateCompare = (a.spentOn ?? '').compareTo(b.spentOn ?? '');
  if (dateCompare != 0) return dateCompare;
  final sortCompare = a.sortOrder.compareTo(b.sortOrder);
  if (sortCompare != 0) return sortCompare;
  return a.id.compareTo(b.id);
}

int _compareFixedPanels(MonthlyPanel a, MonthlyPanel b) {
  final sortCompare = a.sortOrder.compareTo(b.sortOrder);
  if (sortCompare != 0) return sortCompare;
  return a.id.compareTo(b.id);
}

int _comparePlannedEntries(LedgerEntry a, LedgerEntry b) {
  final dueCompare = (a.dueDay ?? 99).compareTo(b.dueDay ?? 99);
  if (dueCompare != 0) return dueCompare;
  final sortCompare = a.sortOrder.compareTo(b.sortOrder);
  if (sortCompare != 0) return sortCompare;
  return a.id.compareTo(b.id);
}
