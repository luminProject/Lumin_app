import 'dart:math';
import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';

class HeroHouse extends StatelessWidget {
  const HeroHouse({super.key});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, c) {
        final w = c.maxWidth;
        final heroW = w.clamp(0.0, 430.0);

        const h = 220.0;
        final houseW = (heroW * 0.58).clamp(200.0, 260.0);
        final calloutW = (heroW * 0.42).clamp(140.0, 175.0);

        return Align(
          alignment: Alignment.center,
          child: SizedBox(
            width: heroW,
            height: h,
            child: Stack(
              children: [
                Center(
                  child: Container(
                    width: min(heroW * 0.80, 280),
                    height: 190,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppColors.mint.withOpacity(0.08),
                    ),
                  ),
                ),
                Center(
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      Container(
                        width: houseW * 0.80,
                        height: 32,
                        decoration: BoxDecoration(
                          color: Colors.black.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(999),
                        ),
                      ),
                      Image.asset(
                        'assets/images/house.png',
                        width: houseW,
                        fit: BoxFit.contain,
                      ),
                    ],
                  ),
                ),
                Positioned(
                  right: 8,
                  top: 8,
                  child: _GlowCallout(
                    width: calloutW,
                    title: 'Solar Production',
                    value: '4.28 kW',
                    icon: Icons.solar_power,
                    glow: AppColors.lime,
                  ),
                ),
                Positioned(
                  left: 8,
                  bottom: 14,
                  child: _GlowCallout(
                    width: calloutW,
                    title: 'Grid',
                    value: '4.28 kW',
                    icon: Icons.electrical_services,
                    glow: AppColors.cyan,
                  ),
                ),
                Positioned(
                  right: 8,
                  bottom: 14,
                  child: _GlowCallout(
                    width: calloutW,
                    title: 'Total Consumption',
                    value: '4.28 kW',
                    icon: Icons.show_chart,
                    glow: AppColors.mint,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _GlowCallout extends StatelessWidget {
  final double width;
  final String title;
  final String value;
  final IconData icon;
  final Color glow;

  const _GlowCallout({
    required this.width,
    required this.title,
    required this.value,
    required this.icon,
    required this.glow,
  });

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: BoxConstraints(minWidth: 120, maxWidth: width),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: glow.withOpacity(0.35), width: 1),
          boxShadow: [
            BoxShadow(
              color: glow.withOpacity(0.25),
              blurRadius: 18,
              spreadRadius: 1,
            ),
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Icon(icon, size: 18, color: glow),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontSize: 10.5, color: AppColors.sub, height: 1.1),
                    maxLines: 2,
                    overflow: TextOverflow.fade,
                    softWrap: true,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    value,
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            )
          ],
        ),
      ),
    );
  }
}
