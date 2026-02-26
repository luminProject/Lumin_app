import 'package:flutter/material.dart';
import '../recommendations/recommendations_page.dart';

import '../../Widgets/gradient_background.dart';
import '../../Widgets/responsive_layout.dart';
import '../../Widgets/home/header.dart';
import '../../Widgets/home/hero_house.dart';
import '../../Widgets/home/solar_impact.dart';
import '../../Widgets/home/devices_section.dart';
import '../../Widgets/home/recommendations_preview.dart';
import '../../Widgets/home/stats_card.dart';
import '../../Widgets/home/bottom_nav.dart';

import '../devices/device_management_page.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  Route _niceRoute(Widget page) {
    return PageRouteBuilder(
      transitionDuration: const Duration(milliseconds: 260),
      reverseTransitionDuration: const Duration(milliseconds: 220),
      pageBuilder: (_, __, ___) => page,
      transitionsBuilder: (_, animation, __, child) {
        final curved = CurvedAnimation(parent: animation, curve: Curves.easeOutCubic);

        final offsetTween = Tween<Offset>(
          begin: const Offset(0.06, 0.0),
          end: Offset.zero,
        ).animate(curved);

        final fadeTween = Tween<double>(begin: 0.0, end: 1.0).animate(curved);

        return FadeTransition(
          opacity: fadeTween,
          child: SlideTransition(
            position: offsetTween,
            child: child,
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final w = MediaQuery.sizeOf(context).width;
    final devicesHeight = (w < 360) ? 168.0 : 158.0;

    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: false,
        bottomNavigationBar: const HomeBottomNav(currentIndex: 0),

        // ✅ المهم: ما نحط padding أفقي هنا عشان ما يتكرر مع ResponsiveLayout
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(0, 10, 0, 18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ✅ يخلي الهيدر ما يلصق فوق عند الكاميرا/الستاتس بار
              SizedBox(height: MediaQuery.of(context).padding.top * 0.25),

              const HomeHeader(),
              const SizedBox(height: 12),

              const HeroHouse(),
              const SizedBox(height: 14),

              const Text(
                'Solar Impact',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 10),

              const SolarImpactRow(),
              const SizedBox(height: 16),

              DevicesSection(
                height: devicesHeight,
                onSeeAll: () {
                  Navigator.of(context).push(
                    _niceRoute(const DeviceManagementPage()),
                  );
                },
              ),
              const SizedBox(height: 16),

              // ✅ Smart Recommendations (Preview) — مكانها الطبيعي قبل الإحصائيات
              RecommendationsPreview(
                onSeeAll: () {
                  Navigator.of(context).push(_niceRoute(const RecommendationsPage()));
                },
              ),

              const SizedBox(height: 16),

              const Text(
                'Statistics',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 10),

              const StatsCardExact(),
            ],
          ),
        ),
      ),
    );
  }
}

/// Placeholder page مؤقتة عشان المشروع يشتغل حتى لو ما عندك صفحة التوصيات جاهزة.
/// لما تجهزين صفحة Recommendations الحقيقية، بس استبدلي هذا الـ page بالصفحة الجديدة.
class _RecommendationsPage extends StatelessWidget {
  const _RecommendationsPage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Smart Recommendations'),
        backgroundColor: Colors.transparent,
      ),
      backgroundColor: Colors.transparent,
      body: const Padding(
        padding: EdgeInsets.all(16),
        child: Text(
          'Put your full Recommendations screen here (tabs: New / History).',
          style: TextStyle(color: Colors.white70),
        ),
      ),
    );
  }
}
