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
  final String? spentOn;
  final int? amountValue;
  final int? dueDay;

  int get effectiveAmount => (amountValue ?? 0) - discountAmount;

  factory MonthlyPanel.fromJson(Map<String, dynamic> json) {
    return MonthlyPanel(
      id: json['id'] as int,
      month: json['month'] as String,
      panelType: json['panel_type'] as String,
      title: json['title'] as String? ?? '',
      sortOrder: _int(json['sort_order']),
      discountAmount: _int(json['discount_amount']),
      spentOn: json['spent_on'] as String?,
      amountValue:
          json['amount_value'] == null ? null : _int(json['amount_value']),
      dueDay: json['due_day'] == null ? null : _int(json['due_day']),
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
  JudgmentState({required this.budget, required this.payment});

  final JudgmentTone budget;
  final JudgmentTone payment;

  factory JudgmentState.fromJson(Map<String, dynamic> json) {
    return JudgmentState(
      budget: JudgmentTone.fromJson(
          json['budget'] as Map<String, dynamic>? ?? const {}),
      payment: JudgmentTone.fromJson(
          json['payment'] as Map<String, dynamic>? ?? const {}),
    );
  }
}

class CardPaymentStatus {
  CardPaymentStatus({
    required this.paymentMonth,
    required this.dueDate,
    required this.effectiveRemainingTotal,
    required this.rows,
  });

  final String paymentMonth;
  final String dueDate;
  final int effectiveRemainingTotal;
  final List<CardPaymentRow> rows;

  factory CardPaymentStatus.fromJson(Map<String, dynamic> json) {
    return CardPaymentStatus(
      paymentMonth: json['payment_month'] as String? ?? '',
      dueDate: json['due_date'] as String? ?? '',
      effectiveRemainingTotal: _int(json['effective_remaining_total']),
      rows: (json['rows'] as List<dynamic>? ?? const [])
          .map((row) => CardPaymentRow.fromJson(row as Map<String, dynamic>))
          .toList(),
    );
  }
}

class CardPaymentRow {
  CardPaymentRow({
    required this.title,
    required this.originalAmount,
    required this.immediatePaidAmount,
    required this.discountAmount,
    required this.remainingAmount,
    required this.paymentKeys,
  });

  final String title;
  final int originalAmount;
  final int immediatePaidAmount;
  final int discountAmount;
  final int remainingAmount;
  final List<String> paymentKeys;

  factory CardPaymentRow.fromJson(Map<String, dynamic> json) {
    return CardPaymentRow(
      title: json['title'] as String? ?? '',
      originalAmount: _int(json['original_amount']),
      immediatePaidAmount: _int(json['immediate_paid_amount']),
      discountAmount: _int(json['discount_amount']),
      remainingAmount: _int(json['remaining_amount']),
      paymentKeys: (json['payment_keys'] as List<dynamic>? ?? const [])
          .map((value) => value.toString())
          .toList(),
    );
  }
}

int _int(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? 0;
  return 0;
}
