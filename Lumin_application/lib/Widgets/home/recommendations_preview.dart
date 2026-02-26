import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import 'glass_card.dart';

class RecommendationsPreview extends StatelessWidget {
  final VoidCallback? onSeeAll;

  const RecommendationsPreview({
    super.key,
    this.onSeeAll,
  });

  @override
  Widget build(BuildContext context) {
    // داتا تجريبية — بعدين اربطيها من الباك/المنطق
    const recs = <_RecItem>[
      _RecItem(
        title: 'Run the washing machine now',
        reason: 'High solar output (4.2 kW) — use solar instead of the grid.',
        savingKwh: 1.2,
        savingSar: 15,
      ),
      _RecItem(
        title: 'Lower AC by 1°C for 2 hours',
        reason: 'Peak consumption detected — small change, good savings.',
        savingKwh: 0.7,
        savingSar: 8,
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ✅ نفس هيدر قسم Devices
        Row(
          children: [
            const Text(
              'Smart Recommendations',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const Spacer(),
            InkWell(
              onTap: onSeeAll,
              borderRadius: BorderRadius.circular(10),
              child: const Padding(
                padding: EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                child: Text(
                  'See all',
                  style: TextStyle(color: AppColors.sub, fontSize: 12),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),

        // ✅ عمودي فوق بعض
        ...recs.map((r) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _RecommendationCard(item: r),
            )),
      ],
    );
  }
}

class _RecItem {
  final String title;
  final String reason;
  final double savingKwh;
  final int savingSar;

  const _RecItem({
    required this.title,
    required this.reason,
    required this.savingKwh,
    required this.savingSar,
  });
}

class _RecommendationCard extends StatelessWidget {
  final _RecItem item;
  const _RecommendationCard({required this.item});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      radius: 20,
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: AppColors.mint.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.flash_on_rounded, color: AppColors.mint, size: 18),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  item.title,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          Text(
            item.reason,
            style: const TextStyle(fontSize: 12, color: AppColors.sub, height: 1.2),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),

          const SizedBox(height: 10),

          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _MiniChip(icon: Icons.bolt_rounded, text: '${item.savingKwh.toStringAsFixed(1)} kWh'),
              _MiniChip(icon: Icons.payments_rounded, text: '~ ${item.savingSar} SAR'),
            ],
          ),
        ],
      ),
    );
  }
}

class _MiniChip extends StatelessWidget {
  final IconData icon;
  final String text;

  const _MiniChip({
    required this.icon,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.mint.withOpacity(0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppColors.mint.withOpacity(0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: AppColors.mint),
          const SizedBox(width: 6),
          Text(
            text,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AppColors.mint),
          ),
        ],
      ),
    );
  }
}
