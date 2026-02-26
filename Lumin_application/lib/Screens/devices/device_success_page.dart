import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';
import 'package:lumin_application/Screens/devices/device_management_page.dart';
class DeviceSuccessPage extends StatelessWidget {
  final String? deviceName; // اختياري
  final VoidCallback? onDone;

  const DeviceSuccessPage({
    super.key,
    this.deviceName,
    this.onDone,
  });

  @override
  Widget build(BuildContext context) {
    return GradientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        extendBodyBehindAppBar: true,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          centerTitle: true,
          title: const Text(
            'Success',
            style: TextStyle(fontWeight: FontWeight.w900),
          ),
          leading: IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          ),
        ),
        body: SafeArea(
          child: Stack(
            children: [
              // ✅ Blur overlay like your screenshot
              Positioned.fill(
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                  child: Container(
                    color: Colors.black.withOpacity(0.10),
                  ),
                ),
              ),

              // ✅ Center card
              Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 18),
                  child: GlassCard(
                    radius: 20,
                    padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Container(
                          width: 56,
                          height: 56,
                          decoration: BoxDecoration(
                            color: AppColors.mint.withOpacity(0.22),
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(color: Colors.white12),
                          ),
                          child: const Icon(
                            Icons.check_rounded,
                            color: AppColors.mint,
                            size: 30,
                          ),
                        ),
                        const SizedBox(height: 12),

                        const Text(
                          'Added successfully!',
                          style: TextStyle(
                            fontSize: 16.5,
                            fontWeight: FontWeight.w900,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 8),

                        Text(
                          deviceName == null
                              ? 'Your device has been added. You can now start tracking energy usage and get smart recommendations.'
                              : '“$deviceName” has been added. You can now start tracking energy usage and get smart recommendations.',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.70),
                            fontWeight: FontWeight.w700,
                            fontSize: 12.5,
                            height: 1.3,
                          ),
                          textAlign: TextAlign.center,
                        ),

                        const SizedBox(height: 16),

                        SizedBox(
                          width: double.infinity,
                          height: 50,
                          child: ElevatedButton(
                            onPressed:  () {
  Navigator.pushAndRemoveUntil(
    context,
    MaterialPageRoute(builder: (_) => const DeviceManagementPage()),
    (route) => false,
  );
},
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.button,
                              elevation: 0,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                            ),
                            child: const Text(
                              'Done',
                              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
