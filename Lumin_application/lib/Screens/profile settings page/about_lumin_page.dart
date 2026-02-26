import 'package:flutter/material.dart';
import 'package:lumin_application/Recomendation/notificationspage.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/theme/app_colors.dart';

class AboutLuminPage extends StatelessWidget {
  const AboutLuminPage({super.key});

  @override
  Widget build(BuildContext context) {
    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: true,
        title: 'About LUMIN',

        // ✅ Sub page: فيها رجوع
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
        ),

        // ✅ مثل باقي صفحاتكم (ممكن تشيلينها لو ما تبين)
        actions: [
          IconButton(
            onPressed: () {
  Navigator.push(
    context,
    MaterialPageRoute(builder: (_) => const NotificationsPage()),
  );
},
            icon: const Icon(Icons.notifications_none_rounded, color: AppColors.mint),
          ),
        ],

        // ✅ لا تحطين bottom nav هنا لأنها صفحة فرعية من Settings
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
             const SizedBox(height:40),
            // ===== Header Card =====
            GlassCard(
              radius: 22,
              padding: const EdgeInsets.all(18),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Logo box
                  Container(
                    width: 46,
                    height: 46,
                    decoration: BoxDecoration(
                      color: AppColors.mint.withOpacity(0.18),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(Icons.bolt_rounded, color: AppColors.mint, size: 24),
                  ),
                  const SizedBox(width: 12),

                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'LUMIN',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Smart energy companion that helps you track usage, '
                          'predict your bill, and understand your solar impact.',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.72),
                            fontSize: 12.8,
                            height: 1.25,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 14),

            // ===== What you can do =====
            GlassCard(
              radius: 22,
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'What you can do',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 15.5,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 12),

                  _bullet(
                    icon: Icons.receipt_long_rounded,
                    title: 'Bill Prediction',
                    desc: 'Set a monthly limit and get smart alerts and recommendations.',
                  ),
                  const SizedBox(height: 10),

                  _bullet(
                    icon: Icons.wb_sunny_rounded,
                    title: 'Solar Forecast',
                    desc: 'View 7-day solar production and weather impact on output.',
                  ),
                  const SizedBox(height: 10),

                  _bullet(
                    icon: Icons.devices_rounded,
                    title: 'Device Management',
                    desc: 'Monitor connected devices and track room-by-room usage.',
                  ),
                  const SizedBox(height: 10),

                  _bullet(
                    icon: Icons.bar_chart_rounded,
                    title: 'Insights & Statistics',
                    desc: 'Understand your consumption trends and savings over time.',
                  ),
                ],
              ),
            ),

            const SizedBox(height: 14),            

            // ===== Version card =====
            GlassCard(
              radius: 22,
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              child: Row(
                children: [
                  Text(
                    'Version',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.78),
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    '1.0.0',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.90),
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 10),
          ],
        ),
      ),
    );
  }

  Widget _bullet({
    required IconData icon,
    required String title,
    required String desc,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 34,
          height: 34,
          decoration: BoxDecoration(
            color: AppColors.mint.withOpacity(0.18),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: AppColors.mint, size: 18),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13.5,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                desc,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.70),
                  fontSize: 12.3,
                  height: 1.2,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}