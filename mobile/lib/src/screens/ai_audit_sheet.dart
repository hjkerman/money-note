import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../ai_audit_report.dart';
import '../app_state.dart';
import '../chatgpt_share_bridge.dart';
import '../theme.dart';

Future<void> showAiAuditSheet(BuildContext context, AppState state) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: moneySurface,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (_) => _AiAuditSheet(state: state),
  );
}

class _AiAuditSheet extends StatefulWidget {
  const _AiAuditSheet({required this.state});

  final AppState state;

  @override
  State<_AiAuditSheet> createState() => _AiAuditSheetState();
}

class _AiAuditSheetState extends State<_AiAuditSheet> {
  final ChatGptShareBridge _shareBridge = ChatGptShareBridge();
  final FixedExtentScrollController _yearController =
      FixedExtentScrollController();
  final FixedExtentScrollController _monthController =
      FixedExtentScrollController();
  AiAuditReportData? _data;
  Object? _error;
  bool _loading = true;
  bool _sharing = false;
  late int _selectedYear;
  late int _selectedMonth;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _yearController.dispose();
    _monthController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final data = await AiAuditReportData.load(
        widget.state.api,
        latestAllowedMonth: widget.state.currentMonth,
      );
      final months = data.availableMonths;
      if (!mounted) return;
      if (months.isNotEmpty) {
        final initial = months.contains(widget.state.currentMonth)
            ? widget.state.currentMonth
            : months.first;
        _selectedYear = int.parse(initial.substring(0, 4));
        _selectedMonth = int.parse(initial.substring(5, 7));
      }
      setState(() {
        _data = data;
        _loading = false;
      });
      if (months.isNotEmpty) {
        WidgetsBinding.instance.addPostFrameCallback((_) => _syncWheels());
      }
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error;
        _loading = false;
      });
    }
  }

  List<int> get _years {
    final years = _data?.availableMonths
            .map((month) => int.parse(month.substring(0, 4)))
            .toSet()
            .toList() ??
        [];
    years.sort();
    return years;
  }

  List<int> get _monthsForYear {
    final months = _data?.availableMonths
            .where((month) => month.startsWith('$_selectedYear-'))
            .map((month) => int.parse(month.substring(5, 7)))
            .toList() ??
        [];
    months.sort();
    return months;
  }

  String get _selectedMonthValue =>
      '$_selectedYear-${_selectedMonth.toString().padLeft(2, '0')}';

  void _syncWheels() {
    if (!mounted || _years.isEmpty || _monthsForYear.isEmpty) return;
    _yearController.jumpToItem(_years.indexOf(_selectedYear));
    _monthController.jumpToItem(_monthsForYear.indexOf(_selectedMonth));
  }

  void _selectYear(int index) {
    final years = _years;
    if (index < 0 || index >= years.length) return;
    final selectedYear = years[index];
    final availableMonths = _data!.availableMonths
        .where((month) => month.startsWith('$selectedYear-'))
        .map((month) => int.parse(month.substring(5, 7)))
        .toList()
      ..sort();
    setState(() {
      _selectedYear = selectedYear;
      if (!availableMonths.contains(_selectedMonth)) {
        _selectedMonth = availableMonths.last;
      }
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _monthController.jumpToItem(_monthsForYear.indexOf(_selectedMonth));
      }
    });
  }

  void _selectMonth(int index) {
    final months = _monthsForYear;
    if (index < 0 || index >= months.length) return;
    setState(() => _selectedMonth = months[index]);
  }

  Future<void> _share() async {
    if (_sharing || _data == null) return;
    setState(() => _sharing = true);
    try {
      final fresh = await AiAuditReportData.load(
        widget.state.api,
        latestAllowedMonth: widget.state.currentMonth,
      );
      if (!fresh.containsMonth(_selectedMonthValue)) {
        throw const ChatGptShareException('선택한 연월의 기록을 찾을 수 없습니다.');
      }
      final markdown = fresh.buildMarkdown(_selectedMonthValue);
      await _shareBridge.shareAudit(
        filename: 'money-note-audit-$_selectedMonthValue.md',
        markdown: markdown,
      );
      if (mounted) Navigator.of(context).pop();
    } catch (error) {
      if (!mounted) return;
      final message = error is ChatGptShareException
          ? error.message
          : '회계감사 자료를 준비하지 못했습니다.';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message)),
      );
      setState(() => _sharing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FractionallySizedBox(
      heightFactor: 0.68,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 10, 20, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 46,
                height: 5,
                decoration: BoxDecoration(
                  color: moneyLine,
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'ChatGPT에게 회계감사 받기',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            const Text('분석할 연월을 선택하세요.', style: TextStyle(color: moneyMuted)),
            const SizedBox(height: 18),
            Expanded(child: _body()),
          ],
        ),
      ),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return _MessageBody(
        message: '장부 연월을 불러오지 못했습니다.',
        actionLabel: '다시 시도',
        onAction: () {
          setState(() {
            _loading = true;
            _error = null;
          });
          _load();
        },
      );
    }
    if (_data!.availableMonths.isEmpty) {
      return const _MessageBody(message: '회계감사할 장부가 없습니다.');
    }
    return Column(
      children: [
        Expanded(
          child: Stack(
            alignment: Alignment.center,
            children: [
              Container(
                height: 52,
                decoration: BoxDecoration(
                  color: moneyGreenSoft.withValues(alpha: 0.55),
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              Row(
                children: [
                  Expanded(
                    child: CupertinoPicker(
                      scrollController: _yearController,
                      itemExtent: 52,
                      selectionOverlay: const SizedBox.shrink(),
                      onSelectedItemChanged: _selectYear,
                      children: _years
                          .map((year) => Center(child: Text('$year년')))
                          .toList(),
                    ),
                  ),
                  Container(width: 1, height: 156, color: moneyLine),
                  Expanded(
                    child: CupertinoPicker(
                      key: ValueKey(_selectedYear),
                      scrollController: _monthController,
                      itemExtent: 52,
                      selectionOverlay: const SizedBox.shrink(),
                      onSelectedItemChanged: _selectMonth,
                      children: _monthsForYear
                          .map((month) => Center(child: Text('$month월')))
                          .toList(),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        const Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.privacy_tip_outlined, size: 20, color: moneyGreen),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                '카드 지출, 현금흐름, 청구, 가족카드 내역이 ChatGPT에 공유됩니다.',
                style: TextStyle(color: moneyMuted, fontSize: 13),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        FilledButton(
          onPressed: _sharing ? null : _share,
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(52),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
          child: Text(_sharing ? '자료 준비 중...' : '회계감사 소집'),
        ),
        TextButton(
          onPressed: _sharing ? null : () => Navigator.of(context).pop(),
          child: const Text('취소'),
        ),
      ],
    );
  }
}

class _MessageBody extends StatelessWidget {
  const _MessageBody({
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(message, textAlign: TextAlign.center),
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    );
  }
}
