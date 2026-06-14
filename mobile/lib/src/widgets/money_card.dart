import 'package:flutter/material.dart';

import '../theme.dart';

class MoneyCard extends StatelessWidget {
  const MoneyCard({
    required this.child,
    super.key,
    this.padding = const EdgeInsets.all(16),
    this.color = moneySurface,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: color,
        border: Border.all(color: moneyLine),
        borderRadius: BorderRadius.circular(20),
      ),
      child: child,
    );
  }
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key, this.trailing});

  final String text;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 22, 4, 10),
      child: Row(
        children: [
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                  fontSize: 18, fontWeight: FontWeight.w800, color: moneyText),
            ),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

class AmountTile extends StatelessWidget {
  const AmountTile({
    required this.label,
    required this.amount,
    super.key,
  });

  final String label;
  final String amount;

  @override
  Widget build(BuildContext context) {
    return MoneyCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(
                  color: moneyMuted, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Text(amount,
              style:
                  const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}
