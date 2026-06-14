class AuthUser {
  AuthUser({
    required this.id,
    required this.username,
    required this.displayName,
    required this.sharePinNeedsChange,
    this.sessionToken,
  });

  final int id;
  final String username;
  final String displayName;
  final bool sharePinNeedsChange;
  final String? sessionToken;

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['id'] as int,
      username: json['username'] as String,
      displayName: json['display_name'] as String,
      sharePinNeedsChange: json['share_pin_needs_change'] as bool? ?? false,
      sessionToken: json['session_token'] as String?,
    );
  }
}

class Summary {
  Summary({
    required this.cardTotal,
    required this.plannedRecurringTotal,
    required this.frozenAssetTotal,
    required this.liquidityStatus,
    required this.nextMonthLiquidity,
  });

  final int cardTotal;
  final int plannedRecurringTotal;
  final int frozenAssetTotal;
  final int liquidityStatus;
  final int nextMonthLiquidity;

  factory Summary.fromJson(Map<String, dynamic> json) {
    return Summary(
      cardTotal: _int(json['card_total']),
      plannedRecurringTotal: _int(json['planned_recurring_total']),
      frozenAssetTotal: _int(json['frozen_asset_total']),
      liquidityStatus: _int(json['liquidity_status']),
      nextMonthLiquidity: _int(json['next_month_liquidity']),
    );
  }
}

class LedgerEntry {
  LedgerEntry({
    required this.id,
    required this.bookSection,
    required this.entryKind,
    required this.title,
    required this.sortOrder,
    this.entryDate,
    this.usagePlace,
    this.usageItem,
    this.amountValue,
    this.spendingCategory,
    this.paymentKey,
    this.discountOverride = 0,
    this.dueDay,
  });

  final int id;
  final String bookSection;
  final String entryKind;
  final String title;
  final int sortOrder;
  final String? entryDate;
  final String? usagePlace;
  final String? usageItem;
  final int? amountValue;
  final String? spendingCategory;
  final String? paymentKey;
  final int discountOverride;
  final int? dueDay;

  bool get isDiscountExcluded => discountOverride != 0;

  int discountForPolicy(bool policyEnabled) {
    if (!policyEnabled || paymentKey == null) return 0;
    if (isDiscountExcluded) return 0;
    return ((amountValue ?? 0) * 0.012).floor();
  }

  int effectiveAmountForPolicy(bool policyEnabled) {
    return (amountValue ?? 0) - discountForPolicy(policyEnabled);
  }

  factory LedgerEntry.fromJson(Map<String, dynamic> json) {
    return LedgerEntry(
      id: json['id'] as int,
      bookSection: json['book_section'] as String,
      entryKind: json['entry_kind'] as String,
      title: json['title'] as String? ?? '',
      sortOrder: _int(json['sort_order']),
      entryDate: json['entry_date'] as String?,
      usagePlace: json['usage_place'] as String?,
      usageItem: json['usage_item'] as String?,
      amountValue:
          json['amount_value'] == null ? null : _int(json['amount_value']),
      spendingCategory: json['spending_category'] as String?,
      paymentKey: json['payment_key'] as String?,
      discountOverride: _int(json['discount_override']),
      dueDay: json['due_day'] == null ? null : _int(json['due_day']),
    );
  }
}

class MonthlyPanel {
  MonthlyPanel({
    required this.id,
    required this.month,
    required this.panelType,
    required this.title,
    required this.sortOrder,
    required this.discountAmount,
    required this.discountOverride,
    this.spentOn,
    this.amountValue,
    this.dueDay,
  });

  final int id;
  final String month;
  final String panelType;
  final String title;
  final int sortOrder;
  final int discountAmount;
  final int discountOverride;
  final String? spentOn;
  final int? amountValue;
  final int? dueDay;

  int get effectiveAmount => (amountValue ?? 0) - discountAmount;
  bool get isDiscountExcluded => discountOverride != 0 && discountAmount <= 0;

  int discountForPolicy(bool policyEnabled) {
    if (!policyEnabled) return 0;
    if (discountOverride != 0) return discountAmount;
    return ((amountValue ?? 0) * 0.012).floor();
  }

  int effectiveAmountForPolicy(bool policyEnabled) {
    return (amountValue ?? 0) - discountForPolicy(policyEnabled);
  }

  factory MonthlyPanel.fromJson(Map<String, dynamic> json) {
    return MonthlyPanel(
      id: json['id'] as int,
      month: json['month'] as String,
      panelType: json['panel_type'] as String,
      title: json['title'] as String? ?? '',
      sortOrder: _int(json['sort_order']),
      discountAmount: _int(json['discount_amount']),
      discountOverride: _int(json['discount_override']),
      spentOn: json['spent_on'] as String?,
      amountValue:
          json['amount_value'] == null ? null : _int(json['amount_value']),
      dueDay: json['due_day'] == null ? null : _int(json['due_day']),
    );
  }
}

class CashFlow {
  CashFlow({
    required this.id,
    required this.occurredOn,
    required this.title,
    required this.amountValue,
    required this.sortOrder,
    required this.isPrimaryIncome,
  });

  final int id;
  final String occurredOn;
  final String title;
  final int amountValue;
  final int sortOrder;
  final bool isPrimaryIncome;

  factory CashFlow.fromJson(Map<String, dynamic> json) {
    return CashFlow(
      id: json['id'] as int,
      occurredOn: json['occurred_on'] as String,
      title: json['title'] as String? ?? '',
      amountValue: _int(json['amount_value']),
      sortOrder: _int(json['sort_order']),
      isPrimaryIncome: _int(json['is_primary_income']) == 1,
    );
  }
}

class CardDiscountMonth {
  CardDiscountMonth({
    required this.month,
    required this.scope,
    required this.policy,
  });

  final String month;
  final String scope;
  final String policy;

  bool get isEnabled => policy == 'enabled';

  factory CardDiscountMonth.fromJson(Map<String, dynamic> json) {
    return CardDiscountMonth(
      month: json['month'] as String? ?? '',
      scope: json['scope'] as String? ?? '',
      policy: json['policy'] as String? ?? 'disabled',
    );
  }
}

class MonthCloseStatus {
  MonthCloseStatus({
    required this.calendarDate,
    required this.calendarMonth,
    required this.needsClose,
    required this.isEarlyClose,
    required this.earlyCloseAvailable,
    required this.earlyCloseStartDay,
    required this.canClose,
    this.oldestOpenMonth,
    this.lastClosedMonth,
  });

  final String calendarDate;
  final String calendarMonth;
  final String? oldestOpenMonth;
  final String? lastClosedMonth;
  final bool needsClose;
  final bool isEarlyClose;
  final bool earlyCloseAvailable;
  final int earlyCloseStartDay;
  final bool canClose;

  factory MonthCloseStatus.fromJson(Map<String, dynamic> json) {
    return MonthCloseStatus(
      calendarDate: json['calendar_date'] as String? ?? '',
      calendarMonth: json['calendar_month'] as String? ?? '',
      oldestOpenMonth: json['oldest_open_month'] as String?,
      lastClosedMonth: json['last_closed_month'] as String?,
      needsClose: json['needs_close'] as bool? ?? false,
      isEarlyClose: json['is_early_close'] as bool? ?? false,
      earlyCloseAvailable: json['early_close_available'] as bool? ?? false,
      earlyCloseStartDay: _int(json['early_close_start_day']),
      canClose: json['can_close'] as bool? ?? false,
    );
  }
}

class AppSettings {
  AppSettings({
    required this.values,
  });

  final Map<String, String> values;

  String get ownerCardLast4 => values['owner_card_last4'] ?? '';
  String get familyCardLast4 => values['family_card_last4'] ?? '';

  factory AppSettings.fromJson(Map<String, dynamic> json) {
    return AppSettings(
        values:
            json.map((key, value) => MapEntry(key, value?.toString() ?? '')));
  }
}

class PendingCardNotification {
  PendingCardNotification({
    required this.id,
    required this.cardLast4,
    required this.monthDay,
    required this.time,
    required this.amount,
    required this.usagePlace,
  });

  final String id;
  final String cardLast4;
  final String monthDay;
  final String time;
  final int amount;
  final String usagePlace;

  factory PendingCardNotification.fromJson(Map<String, dynamic> json) {
    return PendingCardNotification(
      id: json['id'] as String? ?? '',
      cardLast4: json['card_last4'] as String? ?? '',
      monthDay: json['month_day'] as String? ?? '',
      time: json['time'] as String? ?? '',
      amount: _int(json['amount']),
      usagePlace: json['usage_place'] as String? ?? '',
    );
  }
}

class JudgmentTone {
  JudgmentTone({required this.message});

  final String message;

  factory JudgmentTone.fromJson(Map<String, dynamic> json) {
    return JudgmentTone(message: json['message'] as String? ?? '');
  }
}

class JudgmentState {
  JudgmentState({
    required this.budget,
    required this.credit,
    required this.payment,
  });

  final JudgmentTone budget;
  final JudgmentTone credit;
  final JudgmentTone payment;

  factory JudgmentState.fromJson(Map<String, dynamic> json) {
    return JudgmentState(
      budget: JudgmentTone.fromJson(
          json['budget'] as Map<String, dynamic>? ?? const {}),
      credit: JudgmentTone.fromJson(
          json['credit'] as Map<String, dynamic>? ?? const {}),
      payment: JudgmentTone.fromJson(
          json['payment'] as Map<String, dynamic>? ?? const {}),
    );
  }
}

int _int(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? 0;
  return 0;
}
