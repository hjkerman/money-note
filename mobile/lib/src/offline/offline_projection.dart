import '../models.dart';
import 'offline_data.dart';

class OfflineProjection {
  const OfflineProjection({
    required this.summary,
    required this.entries,
    required this.confirmedPlannedEntries,
    required this.panels,
    required this.cashFlows,
    required this.usesConservativeCardEstimate,
  });

  final Summary summary;
  final List<LedgerEntry> entries;
  final List<LedgerEntry> confirmedPlannedEntries;
  final List<MonthlyPanel> panels;
  final List<CashFlow> cashFlows;
  final bool usesConservativeCardEstimate;

  factory OfflineProjection.from(
    OfflineBaseline baseline,
    List<OfflineJournalOperation> operations, {
    DateTime? projectedAt,
  }) {
    final entries = List<LedgerEntry>.from(baseline.entries);
    final confirmedPlanned =
        List<LedgerEntry>.from(baseline.confirmedPlannedEntries);
    final panels = List<MonthlyPanel>.from(baseline.panels);
    final cashFlows = List<CashFlow>.from(baseline.cashFlows);
    final original = baseline.summary;
    var cardTotal = original.cardTotal;
    var spendingTotal = original.currentSpendingTotal;
    var discountTotal = original.currentDiscountTotal;
    var cashFlowBalance = original.cashFlowBalance;
    var remainingLiquidity = original.remainingLiquidity;
    final projectionTime = projectedAt ?? DateTime.now();
    var usesConservativeCardEstimate = false;

    for (final operation in operations) {
      final payload = operation.payload;
      final localId = -1000000 - operation.sequence;
      switch (operation.type) {
        case OfflineOperationType.createCardExpense:
          final amount = _int(payload['amount_value']);
          final requestedOverride =
              _nullableInt(payload['discount_override_amount']);
          final hasValidOverride = requestedOverride != null &&
              requestedOverride >= 0 &&
              requestedOverride <= amount;
          final discountEnabled = payload['discount_enabled'] != false;
          final policyDiscount = hasValidOverride || !discountEnabled
              ? null
              : _estimateAutomaticDiscount(
                  baseline.ownerDiscountMonth,
                  amount,
                );
          final appliedDiscount = hasValidOverride
              ? requestedOverride
              : (discountEnabled ? policyDiscount ?? 0 : 0);
          final effectiveAmount = amount - appliedDiscount;
          final hasExplicitPaymentInput = hasValidOverride || !discountEnabled;
          final hasResolvedEstimate =
              hasExplicitPaymentInput || policyDiscount != null;
          final entryDate = payload['entry_date']?.toString() ?? '';
          final usagePlace = payload['usage_place']?.toString() ?? '';
          final usageItem = payload['usage_item']?.toString() ?? '';
          entries.add(LedgerEntry(
            id: localId,
            bookSection: 'current',
            entryKind: 'expense',
            title: usageItem.isEmpty ? usagePlace : '[$usagePlace] $usageItem',
            sortOrder: localId,
            entryDate: entryDate,
            usagePlace: usagePlace,
            usageItem: usageItem.isEmpty ? null : usageItem,
            amountValue: amount,
            spendingCategory: payload['spending_category'] as String?,
            auxAmountValue: hasExplicitPaymentInput ? appliedDiscount : null,
            discountOverride: hasExplicitPaymentInput ? 1 : 0,
            discountPolicy: hasExplicitPaymentInput
                ? 'offline_override'
                : policyDiscount != null
                    ? baseline.ownerDiscountMonth.policy
                    : 'offline_unknown',
            effectiveDiscountAmount: appliedDiscount,
            effectiveAmountValue: effectiveAmount,
            isOfflinePending: true,
          ));
          spendingTotal += amount;
          discountTotal += appliedDiscount;
          cardTotal += effectiveAmount;
          remainingLiquidity -= effectiveAmount;
          usesConservativeCardEstimate =
              usesConservativeCardEstimate || !hasResolvedEstimate;
          break;
        case OfflineOperationType.createCashFlow:
          final amount = _int(payload['amount_value']);
          final occurredOn = payload['occurred_on']?.toString() ?? '';
          cashFlows.add(CashFlow(
            id: localId,
            occurredOn: occurredOn,
            title: payload['title']?.toString() ?? '',
            amountValue: amount,
            sortOrder: localId,
            isPrimaryIncome: _int(payload['is_primary_income']) == 1,
            isOfflinePending: true,
          ));
          if (_hasOccurred(occurredOn, projectionTime)) {
            cashFlowBalance += amount;
            remainingLiquidity += amount;
          }
          break;
        case OfflineOperationType.confirmFixedExpense:
          final panelId = _int(payload['panel_id']);
          final panelIndex = panels.indexWhere((panel) => panel.id == panelId);
          if (panelIndex < 0) continue;
          final panel = panels[panelIndex];
          final actualAmount = _int(payload['actual_amount']);
          final occurredOn = payload['occurred_on']?.toString() ?? '';
          panels[panelIndex] = MonthlyPanel(
            id: panel.id,
            month: panel.month,
            panelType: panel.panelType,
            title: panel.title,
            sortOrder: panel.sortOrder,
            discountAmount: panel.discountAmount,
            discountOverride: panel.discountOverride,
            discountPolicy: panel.discountPolicy,
            automaticDiscountEligible: panel.automaticDiscountEligible,
            automaticDiscountAmount: panel.automaticDiscountAmount,
            effectiveDiscountAmount: panel.effectiveDiscountAmount,
            effectiveAmountValue: panel.effectiveAmountValue,
            spentOn: occurredOn,
            amountValue: panel.amountValue,
            dueDay: panel.dueDay,
            confirmedAt: operation.createdAt.toIso8601String(),
            confirmedCashFlowId: localId,
            confirmedAmountValue: actualAmount,
            isOfflinePending: true,
          );
          cashFlows.add(CashFlow(
            id: localId,
            occurredOn: occurredOn,
            title: panel.title,
            amountValue: -actualAmount,
            sortOrder: localId,
            isPrimaryIncome: false,
            isOfflinePending: true,
          ));
          final reserve = panel.amountValue ?? 0;
          cashFlowBalance -= actualAmount;
          remainingLiquidity += reserve - actualAmount;
          break;
        case OfflineOperationType.confirmPlannedCardExpense:
          final entryId = _int(payload['entry_id']);
          final entryIndex = entries.indexWhere((entry) => entry.id == entryId);
          if (entryIndex < 0) continue;
          final template = entries.removeAt(entryIndex);
          final actualAmount = _int(payload['actual_amount']);
          final entryDate = payload['entry_date']?.toString() ?? '';
          entries.add(LedgerEntry(
            id: localId,
            bookSection: 'current',
            entryKind: 'expense',
            title: template.title,
            sortOrder: localId,
            entryDate: entryDate,
            usagePlace: template.usagePlace,
            usageItem: template.usageItem,
            amountValue: actualAmount,
            discountPolicy: 'offline_unknown',
            isOfflinePending: true,
          ));
          confirmedPlanned.add(LedgerEntry(
            id: template.id,
            bookSection: template.bookSection,
            entryKind: template.entryKind,
            title: template.title,
            sortOrder: template.sortOrder,
            entryDate: entryDate,
            usagePlace: template.usagePlace,
            usageItem: template.usageItem,
            amountValue: template.amountValue,
            dueDay: template.dueDay,
            confirmedMonth: baseline.monthCloseStatus.calendarMonth,
            confirmedAmountValue: actualAmount,
            isOfflinePending: true,
          ));
          spendingTotal += actualAmount;
          cardTotal += actualAmount;
          remainingLiquidity += (template.amountValue ?? 0) - actualAmount;
          usesConservativeCardEstimate = true;
          break;
      }
    }

    return OfflineProjection(
      summary: Summary(
        scheduledIncome: original.scheduledIncome,
        cardTotal: cardTotal,
        currentSpendingTotal: spendingTotal,
        currentDiscountTotal: discountTotal,
        plannedRecurringTotal: original.plannedRecurringTotal,
        fixedCashTotal: original.fixedCashTotal,
        frozenAssetTotal: original.frozenAssetTotal,
        cashFlowBalance: cashFlowBalance,
        remainingLiquidity: remainingLiquidity,
        claimOriginalTotal: original.claimOriginalTotal,
        claimNetTotal: original.claimNetTotal,
        familyCardOriginalTotal: original.familyCardOriginalTotal,
        familyCardNetTotal: original.familyCardNetTotal,
        visibleCashFlowTotal: original.visibleCashFlowTotal,
      ),
      entries: List.unmodifiable(entries),
      confirmedPlannedEntries: List.unmodifiable(confirmedPlanned),
      panels: List.unmodifiable(panels),
      cashFlows: List.unmodifiable(cashFlows),
      usesConservativeCardEstimate: usesConservativeCardEstimate,
    );
  }
}

int? _estimateAutomaticDiscount(
  CardDiscountMonth discountMonth,
  int amount,
) {
  if (amount < 0 || !discountMonth.isEnabled) {
    return amount < 0 ? null : 0;
  }
  final policy = discountMonth.projectionPolicy;
  if (policy == null || policy.schemaVersion != 1 || policy.policyId.isEmpty) {
    return null;
  }
  if (policy.type == 'no_automatic_discount') return 0;
  if (policy.type != 'flat_statement' || policy.rounding != 'floor') {
    return null;
  }
  return _floorDecimalRate(amount, policy.rate);
}

int? _floorDecimalRate(int amount, String? rawRate) {
  final match = RegExp(r'^(0|[1-9]\d*)(?:\.(\d+))?$').firstMatch(rawRate ?? '');
  if (match == null) return null;
  final fraction = match.group(2) ?? '';
  if (fraction.length > 9) return null;
  var denominator = 1;
  for (var index = 0; index < fraction.length; index += 1) {
    denominator *= 10;
  }
  final whole = int.tryParse(match.group(1)!);
  final fractional = fraction.isEmpty ? 0 : int.tryParse(fraction);
  if (whole == null || fractional == null) return null;
  final numerator = whole * denominator + fractional;
  if (numerator < 0 || numerator > denominator) return null;
  return amount * numerator ~/ denominator;
}

bool _hasOccurred(String occurredOn, DateTime projectedAt) {
  final local = projectedAt.toLocal();
  final createdDate =
      '${local.year.toString().padLeft(4, '0')}-${local.month.toString().padLeft(2, '0')}-${local.day.toString().padLeft(2, '0')}';
  return occurredOn.compareTo(createdDate) <= 0;
}

int _int(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

int? _nullableInt(Object? value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value.toString());
}
