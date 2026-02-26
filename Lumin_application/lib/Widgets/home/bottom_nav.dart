import 'package:flutter/material.dart';
import 'package:lumin_application/Screens/bill_predection/bill_prediction.dart';
import 'package:lumin_application/Screens/profile%20settings%20page/profile_settings_page.dart';
import 'package:lumin_application/Screens/home/home_page.dart';
import 'package:lumin_application/Screens/devices/device_management_page.dart';
import 'package:lumin_application/Screens/solar%20forecast/solar_forecast.dart';
import '../../theme/app_colors.dart';

class HomeBottomNav extends StatelessWidget {
  /// 0 = Home, 1 = Bill Prediction, 2 = Solar Forecast, 3 = Devices, 4 = Profile/Settings
  final int currentIndex;

  const HomeBottomNav({super.key, required this.currentIndex});

  void _goTo(BuildContext context, Widget page, int targetIndex) {
    final forward = targetIndex > currentIndex;
    Navigator.of(context).pushReplacement(_smoothRoute(page, forward: forward));
  }

  Route _smoothRoute(Widget page, {required bool forward}) {
    return PageRouteBuilder(
      transitionDuration: const Duration(milliseconds: 260),
      reverseTransitionDuration: const Duration(milliseconds: 220),
      pageBuilder: (_, __, ___) => page,
      transitionsBuilder: (_, animation, __, child) {
        final curved = CurvedAnimation(
          parent: animation,
          curve: Curves.easeOutCubic,
          reverseCurve: Curves.easeInCubic,
        );

        final begin = Offset(forward ? 0.06 : -0.06, 0.0);
        final slide = Tween<Offset>(begin: begin, end: Offset.zero).animate(curved);
        final fade = Tween<double>(begin: 0.0, end: 1.0).animate(curved);

        return SlideTransition(
          position: slide,
          child: FadeTransition(opacity: fade, child: child),
        );
      },
    );
  }

  Widget _navItem({
    required IconData icon,
    required bool active,
    required VoidCallback onTap,
  }) {
    // ✅ بدون width ثابت — نخليه يتمدد عبر Expanded
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: SizedBox(
        height: 46,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 22,
                color: active ? AppColors.mint : Colors.white54,
              ),
              const SizedBox(height: 6),
              AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                curve: Curves.easeOutCubic,
                width: active ? 22 : 0,
                height: 2.5,
                decoration: BoxDecoration(
                  color: AppColors.mint,
                  borderRadius: BorderRadius.circular(99),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        // ✅ خففنا شوي عشان ما يضيق على الشاشات الصغيرة
        margin: const EdgeInsets.fromLTRB(14, 0, 14, 10),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white10,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white12),
        ),
        child: Row(
          children: [
            Expanded(
              child: _navItem(
                icon: Icons.home_rounded,
                active: currentIndex == 0,
                onTap: () {
                  if (currentIndex != 0) _goTo(context, const HomePage(), 0);
                },
              ),
            ),
            Expanded(
              child: _navItem(
                icon: Icons.receipt_long_rounded,
                active: currentIndex == 1,
                onTap: () {
                  if (currentIndex != 1) _goTo(context, const BillPredictionPage(), 1);
                },
              ),
            ),
            Expanded(
              child: _navItem(
                icon: Icons.wb_sunny_rounded,
                active: currentIndex == 2,
                onTap: () {
                  if (currentIndex != 2) _goTo(context, const SolarForecastPage(), 2);
                },
              ),
            ),
            Expanded(
              child: _navItem(
                icon: Icons.devices_rounded,
                active: currentIndex == 3,
                onTap: () {
                  if (currentIndex != 3) _goTo(context, const DeviceManagementPage(), 3);
                },
              ),
            ),
            Expanded(
              child: _navItem(
                icon: Icons.person_rounded,
                active: currentIndex == 4,
                onTap: () {
                  if (currentIndex != 4) _goTo(context, const ProfileSettingsPage(), 4);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
