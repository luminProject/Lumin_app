import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/theme/app_colors.dart';

class PrivacyPage extends StatelessWidget {
  const PrivacyPage({super.key});

  @override
  Widget build(BuildContext context) {
    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: true,
        title: 'Privacy',
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
        ),
        actions: const [],

        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 40),

            // ===== Intro =====
            GlassCard(
              radius: 22,
              padding: const EdgeInsets.all(18),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: AppColors.mint.withOpacity(0.18),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(
                      Icons.privacy_tip_rounded,
                      color: AppColors.mint,
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Your privacy matters to us. LUMIN is designed to help you '
                      'monitor and optimize your energy usage while keeping your '
                      'personal data protected.',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.75),
                        fontSize: 13,
                        height: 1.3,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 14),

            // ===== What we collect =====
            _sectionCard(
              title: 'Information We Collect',
              icon: Icons.storage_rounded,
              content:
                  '• Energy usage and consumption data\n'
                  '• Connected device information\n'
                  '• User preferences and app settings\n\n'
                  'This data is used only to provide insights, predictions, '
                  'and personalized recommendations.',
            ),

            const SizedBox(height: 14),

            // ===== How we use it =====
            _sectionCard(
              title: 'How We Use Your Data',
              icon: Icons.analytics_rounded,
              content:
                  '• Generate bill predictions\n'
                  '• Improve solar forecasts\n'
                  '• Provide smart recommendations\n'
                  '• Enhance overall app experience',
            ),

            const SizedBox(height: 14),

            // ===== Security =====
            _sectionCard(
              title: 'Data Security',
              icon: Icons.lock_rounded,
              content:
                  'We apply security best practices to protect your data. '
                  'Sensitive information is handled securely and will not be '
                  'shared without your consent.',
            ),

            const SizedBox(height: 10),
          ],
        ),
      ),
    );
  }

  Widget _sectionCard({
    required String title,
    required IconData icon,
    required String content,
  }) {
    return GlassCard(
      radius: 22,
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppColors.mint.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: AppColors.mint, size: 18),
              ),
              const SizedBox(width: 10),
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14.5,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            content,
            style: TextStyle(
              color: Colors.white.withOpacity(0.72),
              fontSize: 12.8,
              height: 1.35,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}