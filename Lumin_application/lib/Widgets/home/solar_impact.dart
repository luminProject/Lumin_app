import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import 'glass_card.dart';

class SolarImpactRow extends StatelessWidget {
  const SolarImpactRow({super.key});

  @override
  Widget build(BuildContext context) {
    return const Row(
      children: [
        Expanded(
          child: _ImpactCard(
            title: 'Money Saved',
            value: '﷼ 18.50',
            sub: 'Saved so far',
            icon: Icons.savings,
            accent: AppColors.cyan,
          ),
        ),
        SizedBox(width: 12),
        Expanded(
          child: _ImpactCard(
            title: 'Carbon Reduction',
            value: '24.6 kg',
            sub: 'CO₂ saved so far',
            icon: Icons.eco,
            accent: AppColors.mint,
          ),
        ),
      ],
    );
  }
}

class _ImpactCard extends StatelessWidget {
  final String title, value, sub;
  final IconData icon;
  final Color accent;

  const _ImpactCard({
    required this.title,
    required this.value,
    required this.sub,
    required this.icon,
    required this.accent,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      radius: 18,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            height: 30,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(fontSize: 12, color: AppColors.sub, height: 1.1),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    color: accent.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, color: accent, size: 18),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
          ),
          const SizedBox(height: 4),
          Text(
            sub,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 12, color: accent.withOpacity(0.85)),
          ),
        ],
      ),
    );
  }
}
