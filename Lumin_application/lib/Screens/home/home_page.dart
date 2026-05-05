import 'dart:async';
import 'package:flutter/material.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
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
import '../../services/api_service.dart';

import '../devices/device_management_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {

  // ─── Real-Time State ──────────────────────────────────────
  final _api = ApiService();
  Timer? _realtimeTimer;

  // HeroHouse
  String _solarText       = '— kWh';
  String _consumptionText = '— kWh';
  String _gridText        = '— kWh';

  // Solar Impact (from energycalculation — updates every minute)
  String _moneySaved      = '— ﷼';
  String _carbonReduction = '— kg';

  @override
  void initState() {
    super.initState();
    _setupFCMListeners();
    _fetchAll();
    _realtimeTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _fetchAll(),
    );
  }

  @override
  void dispose() {
    _realtimeTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchAll() async {
    await Future.wait([
      _fetchRealtimeData(),
      _fetchSolarImpact(),
    ]);
  }

  // ─── Real-Time (device table) ─────────────────────────────
  Future<void> _fetchRealtimeData() async {
    try {
      final data = await _api.getRealtimeData();
      if (!mounted) return;
      setState(() {
        _solarText       = _fmtKwh(data['solar_production_kwh']);
        _consumptionText = _fmtKwh(data['total_consumption_kwh']);
        _gridText        = _fmtKwh(data['grid_kwh']);
      });
    } catch (_) {}
  }

  // ─── Solar Impact (energycalculation) ────────────────────
  Future<void> _fetchSolarImpact() async {
    try {
      final userId = Supabase.instance.client.auth.currentUser?.id;
      if (userId == null) return;

      final res = await Supabase.instance.client
          .from('energycalculation')
          .select('cost_savings, carbon_reduction')
          .eq('user_id', userId)
          .eq('date', DateTime.now().toIso8601String().substring(0, 10))
          .limit(1)
          .maybeSingle();

      if (!mounted || res == null) return;

      final savings  = (res['cost_savings']  as num?)?.toDouble() ?? 0.0;
      final carbon   = (res['carbon_reduction'] as num?)?.toDouble() ?? 0.0;

      setState(() {
        _moneySaved      = '﷼ ${savings.toStringAsFixed(2)}';
        _carbonReduction = '${carbon.toStringAsFixed(2)} kg';
      });
    } catch (_) {}
  }

  // ─── Helpers ─────────────────────────────────────────────
  String _fmtKwh(dynamic v) {
    if (v == null) return '— kWh';
    final kwh = (v as num).toDouble();
    if (kwh < 0.001) return '0.00 kWh';
    if (kwh < 1.0) return '${(kwh * 1000).toStringAsFixed(1)} Wh';
    return '${kwh.toStringAsFixed(3)} kWh';
  }

  void _setupFCMListeners() {
    // لما التطبيق شغال في الفورغراوند
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      final notification = message.notification;
      if (notification == null) return;
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          behavior: SnackBarBehavior.floating,
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          backgroundColor: const Color(0xFF0F2A33),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: const BorderSide(color: Color(0xFF00BFA5), width: 1.4),
          ),
          duration: const Duration(seconds: 5),
          content: Row(
            children: [
              const Icon(Icons.lightbulb_outline, color: Color(0xFF00BFA5)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      notification.title ?? 'Lumin',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                      ),
                    ),
                    Text(
                      notification.body ?? '',
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    });
  }

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

              HeroHouse(
                solarProductionText: _solarText,
                totalConsumptionText: _consumptionText,
                gridText: _gridText,
              ),
              const SizedBox(height: 14),

              const Text(
                'Solar Impact',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 10),

              SolarImpactRow(
                moneySaved: _moneySaved,
                carbonReduction: _carbonReduction,
              ),
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