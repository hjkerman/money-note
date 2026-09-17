import '../models.dart';

enum ConnectivityMode {
  online,
  offline,
  reconciliationRequired;

  String get storageValue => switch (this) {
        online => 'ONLINE',
        offline => 'OFFLINE',
        reconciliationRequired => 'RECONCILIATION_REQUIRED',
      };

  static ConnectivityMode fromStorageValue(Object? value) {
    return switch (value) {
      'OFFLINE' => offline,
      'RECONCILIATION_REQUIRED' => reconciliationRequired,
      _ => online,
    };
  }
}

enum ReconciliationChoice {
  applyToServer,
  discardAndUseServer;

  String get storageValue => switch (this) {
        applyToServer => 'APPLY_TO_SERVER',
        discardAndUseServer => 'DISCARD_AND_USE_SERVER',
      };

  static ReconciliationChoice? fromStorageValue(Object? value) {
    return switch (value) {
      'APPLY_TO_SERVER' => applyToServer,
      'DISCARD_AND_USE_SERVER' => discardAndUseServer,
      _ => null,
    };
  }
}

enum OfflineOperationType {
  createCardExpense,
  createCashFlow,
  confirmFixedExpense,
  confirmPlannedCardExpense;

  String get storageValue => switch (this) {
        createCardExpense => 'CREATE_CARD_EXPENSE',
        createCashFlow => 'CREATE_CASH_FLOW',
        confirmFixedExpense => 'CONFIRM_FIXED_EXPENSE',
        confirmPlannedCardExpense => 'CONFIRM_PLANNED_CARD_EXPENSE',
      };

  static OfflineOperationType fromStorageValue(Object? value) {
    return switch (value) {
      'CREATE_CARD_EXPENSE' => createCardExpense,
      'CREATE_CASH_FLOW' => createCashFlow,
      'CONFIRM_FIXED_EXPENSE' => confirmFixedExpense,
      'CONFIRM_PLANNED_CARD_EXPENSE' => confirmPlannedCardExpense,
      _ => throw const FormatException('unknown offline operation type'),
    };
  }
}

class OfflineWorkspaceMetadata {
  const OfflineWorkspaceMetadata({
    required this.mode,
    this.reconciliationChoice,
  });

  static const schemaVersion = 1;

  final ConnectivityMode mode;
  final ReconciliationChoice? reconciliationChoice;

  Map<String, dynamic> toJson() => {
        'schema_version': schemaVersion,
        'mode': mode.storageValue,
        'reconciliation_choice': reconciliationChoice?.storageValue,
      };

  factory OfflineWorkspaceMetadata.fromJson(Map<String, dynamic> json) {
    if (json['schema_version'] != schemaVersion) {
      throw const FormatException('unsupported offline state schema');
    }
    return OfflineWorkspaceMetadata(
      mode: ConnectivityMode.fromStorageValue(json['mode']),
      reconciliationChoice:
          ReconciliationChoice.fromStorageValue(json['reconciliation_choice']),
    );
  }

  OfflineWorkspaceMetadata copyWith({
    ConnectivityMode? mode,
    ReconciliationChoice? reconciliationChoice,
    bool clearReconciliationChoice = false,
  }) {
    return OfflineWorkspaceMetadata(
      mode: mode ?? this.mode,
      reconciliationChoice: clearReconciliationChoice
          ? null
          : reconciliationChoice ?? this.reconciliationChoice,
    );
  }
}

class OfflineJournalOperation {
  const OfflineJournalOperation({
    required this.operationId,
    required this.type,
    required this.payload,
    required this.createdAt,
    required this.sequence,
    this.status = 'pending',
  });

  static const schemaVersion = 1;

  final String operationId;
  final OfflineOperationType type;
  final Map<String, dynamic> payload;
  final DateTime createdAt;
  final int sequence;
  final String status;

  Map<String, dynamic> toJson() => {
        'schema_version': schemaVersion,
        'operation_id': operationId,
        'operation_type': type.storageValue,
        'payload': payload,
        'created_at': createdAt.toUtc().toIso8601String(),
        'sequence': sequence,
        'status': status,
      };

  factory OfflineJournalOperation.fromJson(Map<String, dynamic> json) {
    if (json['schema_version'] != schemaVersion) {
      throw const FormatException('unsupported offline journal schema');
    }
    final operationId = json['operation_id'];
    final payload = json['payload'];
    final createdAt = DateTime.tryParse(json['created_at']?.toString() ?? '');
    final sequence = json['sequence'];
    final status = json['status'];
    if (operationId is! String ||
        operationId.isEmpty ||
        payload is! Map<String, dynamic> ||
        createdAt == null ||
        sequence is! int ||
        sequence < 1 ||
        status != 'pending') {
      throw const FormatException('invalid offline journal operation');
    }
    return OfflineJournalOperation(
      operationId: operationId,
      type: OfflineOperationType.fromStorageValue(json['operation_type']),
      payload: Map<String, dynamic>.unmodifiable(payload),
      createdAt: createdAt.toUtc(),
      sequence: sequence,
      status: status as String,
    );
  }
}

class OfflineBaseline {
  const OfflineBaseline({
    required this.syncedAt,
    required this.user,
    required this.summary,
    required this.cardPaymentStatus,
    required this.judgment,
    required this.monthCloseStatus,
    required this.settings,
    required this.ownerDiscountMonth,
    required this.familyDiscountMonth,
    required this.transitDiscountProfile,
    required this.entries,
    required this.confirmedPlannedEntries,
    required this.panels,
    required this.cashFlows,
  });

  static const schemaVersion = 1;

  final DateTime syncedAt;
  final AuthUser user;
  final Summary summary;
  final CardPaymentStatus cardPaymentStatus;
  final JudgmentState judgment;
  final MonthCloseStatus monthCloseStatus;
  final AppSettings settings;
  final CardDiscountMonth ownerDiscountMonth;
  final CardDiscountMonth familyDiscountMonth;
  final TransitDiscountProfileStatus transitDiscountProfile;
  final List<LedgerEntry> entries;
  final List<LedgerEntry> confirmedPlannedEntries;
  final List<MonthlyPanel> panels;
  final List<CashFlow> cashFlows;

  Map<String, dynamic> toJson() => {
        'schema_version': schemaVersion,
        'synced_at': syncedAt.toUtc().toIso8601String(),
        'user': _authUserToJson(user),
        'summary': _summaryToJson(summary),
        'card_payment_status': _cardPaymentStatusToJson(cardPaymentStatus),
        'judgment': _judgmentToJson(judgment),
        'month_close_status': _monthCloseStatusToJson(monthCloseStatus),
        'settings': Map<String, String>.from(settings.values),
        'owner_discount_month': _cardDiscountMonthToJson(ownerDiscountMonth),
        'family_discount_month': _cardDiscountMonthToJson(familyDiscountMonth),
        'transit_discount_profile':
            _transitDiscountProfileToJson(transitDiscountProfile),
        'entries': entries.map(_ledgerEntryToJson).toList(),
        'confirmed_planned_entries':
            confirmedPlannedEntries.map(_ledgerEntryToJson).toList(),
        'panels': panels.map(_monthlyPanelToJson).toList(),
        'cash_flows': cashFlows.map(_cashFlowToJson).toList(),
      };

  factory OfflineBaseline.fromJson(Map<String, dynamic> json) {
    if (json['schema_version'] != schemaVersion) {
      throw const FormatException('unsupported offline baseline schema');
    }
    final syncedAt = DateTime.tryParse(json['synced_at']?.toString() ?? '');
    if (syncedAt == null) {
      throw const FormatException('offline baseline sync timestamp is missing');
    }
    return OfflineBaseline(
      syncedAt: syncedAt.toUtc(),
      user: AuthUser.fromJson(_map(json, 'user')),
      summary: Summary.fromJson(_map(json, 'summary')),
      cardPaymentStatus:
          CardPaymentStatus.fromJson(_map(json, 'card_payment_status')),
      judgment: JudgmentState.fromJson(_map(json, 'judgment')),
      monthCloseStatus:
          MonthCloseStatus.fromJson(_map(json, 'month_close_status')),
      settings: AppSettings.fromJson(_map(json, 'settings')),
      ownerDiscountMonth:
          CardDiscountMonth.fromJson(_map(json, 'owner_discount_month')),
      familyDiscountMonth:
          CardDiscountMonth.fromJson(_map(json, 'family_discount_month')),
      transitDiscountProfile: TransitDiscountProfileStatus.fromJson(
          _map(json, 'transit_discount_profile')),
      entries: _list(json, 'entries').map(LedgerEntry.fromJson).toList(),
      confirmedPlannedEntries: _list(json, 'confirmed_planned_entries')
          .map(LedgerEntry.fromJson)
          .toList(),
      panels: _list(json, 'panels').map(MonthlyPanel.fromJson).toList(),
      cashFlows: _list(json, 'cash_flows').map(CashFlow.fromJson).toList(),
    );
  }
}

class OfflineReconciliationBundle {
  const OfflineReconciliationBundle({
    required this.baseline,
    required this.operations,
    required this.choice,
  });

  final OfflineBaseline baseline;
  final List<OfflineJournalOperation> operations;
  final ReconciliationChoice? choice;
}

Map<String, dynamic> _map(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! Map<String, dynamic>) {
    throw FormatException('$key must be an object');
  }
  return value;
}

List<Map<String, dynamic>> _list(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! List) throw FormatException('$key must be a list');
  return value.map((item) {
    if (item is! Map<String, dynamic>) {
      throw FormatException('$key items must be objects');
    }
    return item;
  }).toList();
}

Map<String, dynamic> _authUserToJson(AuthUser value) => {
      'id': value.id,
      'username': value.username,
      'display_name': value.displayName,
      'share_pin_needs_change': value.sharePinNeedsChange,
      'session_token': null,
    };

Map<String, dynamic> _summaryToJson(Summary value) => {
      'scheduled_income': value.scheduledIncome,
      'card_total': value.cardTotal,
      'current_spending_total': value.currentSpendingTotal,
      'current_discount_total': value.currentDiscountTotal,
      'planned_recurring_total': value.plannedRecurringTotal,
      'fixed_cash_total': value.fixedCashTotal,
      'frozen_asset_total': value.frozenAssetTotal,
      'cash_flow_balance': value.cashFlowBalance,
      'remaining_liquidity': value.remainingLiquidity,
      'claim_original_total': value.claimOriginalTotal,
      'claim_net_total': value.claimNetTotal,
      'family_card_original_total': value.familyCardOriginalTotal,
      'family_card_net_total': value.familyCardNetTotal,
      'visible_cash_flow_total': value.visibleCashFlowTotal,
    };

Map<String, dynamic> _cardPaymentStatusToJson(CardPaymentStatus value) => {
      'effective_remaining_total': value.effectiveRemainingTotal,
    };

Map<String, dynamic> _ledgerEntryToJson(LedgerEntry value) => {
      'id': value.id,
      'book_section': value.bookSection,
      'entry_kind': value.entryKind,
      'title': value.title,
      'sort_order': value.sortOrder,
      'entry_date': value.entryDate,
      'usage_place': value.usagePlace,
      'usage_item': value.usageItem,
      'amount_value': value.amountValue,
      'spending_category': value.spendingCategory,
      'payment_key': value.paymentKey,
      'aux_amount_value': value.auxAmountValue,
      'discount_override': value.discountOverride,
      'discount_policy': value.discountPolicy,
      'automatic_discount_eligible': value.automaticDiscountEligible,
      'automatic_discount_amount': value.automaticDiscountAmount,
      'effective_discount_amount': value.effectiveDiscountAmount,
      'effective_amount_value': value.effectiveAmountValue,
      'is_transport': value.isTransport,
      'is_toll': value.isToll,
      'due_day': value.dueDay,
      'confirmed_month': value.confirmedMonth,
      'confirmed_amount_value': value.confirmedAmountValue,
      'confirmed_effective_discount_amount':
          value.confirmedEffectiveDiscountAmount,
      'confirmed_effective_amount_value': value.confirmedEffectiveAmountValue,
    };

Map<String, dynamic> _monthlyPanelToJson(MonthlyPanel value) => {
      'id': value.id,
      'month': value.month,
      'panel_type': value.panelType,
      'title': value.title,
      'sort_order': value.sortOrder,
      'discount_amount': value.discountAmount,
      'discount_override': value.discountOverride,
      'discount_policy': value.discountPolicy,
      'automatic_discount_eligible': value.automaticDiscountEligible,
      'automatic_discount_amount': value.automaticDiscountAmount,
      'effective_discount_amount': value.effectiveDiscountAmount,
      'effective_amount_value': value.effectiveAmountValue,
      'spent_on': value.spentOn,
      'amount_value': value.amountValue,
      'due_day': value.dueDay,
      'confirmed_at': value.confirmedAt,
      'confirmed_cash_flow_id': value.confirmedCashFlowId,
      'confirmed_amount_value': value.confirmedAmountValue,
    };

Map<String, dynamic> _cashFlowToJson(CashFlow value) => {
      'id': value.id,
      'occurred_on': value.occurredOn,
      'title': value.title,
      'amount_value': value.amountValue,
      'sort_order': value.sortOrder,
      'is_primary_income': value.isPrimaryIncome ? 1 : 0,
    };

Map<String, dynamic> _cardDiscountMonthToJson(CardDiscountMonth value) => {
      'month': value.month,
      'scope': value.scope,
      'policy': value.policy,
    };

Map<String, dynamic> _transitDiscountProfileToJson(
        TransitDiscountProfileStatus value) =>
    {
      'month': value.month,
      'profile': value.profile,
    };

Map<String, dynamic> _monthCloseStatusToJson(MonthCloseStatus value) => {
      'calendar_date': value.calendarDate,
      'calendar_month': value.calendarMonth,
      'oldest_open_month': value.oldestOpenMonth,
      'last_closed_month': value.lastClosedMonth,
      'needs_close': value.needsClose,
      'is_early_close': value.isEarlyClose,
      'early_close_available': value.earlyCloseAvailable,
      'early_close_start_day': value.earlyCloseStartDay,
      'can_close': value.canClose,
      'unconfirmed_recurring_items': value.unconfirmedRecurringItems
          .map((item) => {
                'kind': item.kind,
                'id': item.id,
                'title': item.title,
                'detail': item.detail,
                'amount_value': item.amountValue,
                'due_day': item.dueDay,
              })
          .toList(),
    };

Map<String, dynamic> _judgmentToJson(JudgmentState value) => {
      'budget': {'message': value.budget.message},
      'credit': {'message': value.credit.message},
      'payment': {'message': value.payment.message},
    };
