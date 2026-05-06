import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';
import 'package:lumin_application/Screens/devices/device_setup_page.dart';
import 'package:lumin_application/services/api_service.dart';

class AddDevicePage extends StatefulWidget {
  const AddDevicePage({super.key});

  @override
  State<AddDevicePage> createState() => _AddDevicePageState();
}

class _AddDevicePageState extends State<AddDevicePage> {
  final ApiService _apiService = ApiService();
  bool _loading = false;

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  String _normalizeDeviceType(String raw) {
    final v = raw.trim().toLowerCase();

    // Accept common variants coming from scan/pairing screens.
    if (v == 'production' || v == 'prod' || v == 'solar' || v == 'generation') {
      return 'production';
    }
    if (v == 'consumption' || v == 'cons' || v == 'usage' || v == 'load') {
      return 'consumption';
    }

    // If already one of the expected values, keep it.
    if (v == 'production' || v == 'consumption') return v;

    // Otherwise return as-is (after trim) so existing validation behavior remains unchanged.
    return raw.trim();
  }

  Future<void> _openSetupAndSave() async {
    if (_loading) return;
    setState(() => _loading = true);

    try {
      // Open manual device setup directly without sensor pairing.
      final result = await Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => const DeviceSetupPage(deviceId: 'manual_setup'),
        ),
      );

      if (!mounted) return;
      if (result == null) {
        setState(() => _loading = false);
        return;
      }

      // If the search page already handles saving and returns `true`, just close and refresh.
      if (result == true) {
        Navigator.pop(context, true);
        return;
      }

      // Otherwise, try to read device details from a returned Map.
      if (result is Map) {
        final name = (result['device_name'] ?? result['name'] ?? '')
            .toString()
            .trim();
        final type = (result['device_type'] ?? result['type'] ?? '')
            .toString()
            .trim();
        final panelCapacity = (result['panel_capacity'] ?? '')
            .toString()
            .trim();
        final room = (result['room'] ?? '').toString().trim();
        final isShiftable = result['is_shiftable'] == true;

        if (name.isEmpty || type.isEmpty) {
          _snack('Setup finished, but device info is missing.');
          setState(() => _loading = false);
          return;
        }

        final normalizedType = _normalizeDeviceType(type);
        await _apiService.addDevice(
          deviceName: name,
          deviceType: normalizedType,
          panelCapacity: panelCapacity.isEmpty ? null : panelCapacity,
          room: room.isEmpty ? null : room,
          isShiftable: normalizedType == 'consumption' ? isShiftable : false,
        );

        if (!mounted) return;
        _snack('Device added successfully ✅');
        Navigator.pop(context, true);
        return;
      }

      // Unknown return type
      _snack('Setup finished, but could not read device info.');
    } catch (e) {
      if (!mounted) return;
      _snack('Error: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.ltr,
      child: GradientBackground(
        child: ResponsiveLayout(
          showAppBar: true,
          title: 'Add Device',
          leading: IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(
              Icons.arrow_back_ios_new_rounded,
              color: Colors.white,
            ),
          ),
          actions: const [],
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 18),

              // ===== Icon =====
              Center(
                child: Container(
                  width: 62,
                  height: 62,
                  decoration: BoxDecoration(
                    color: AppColors.mint.withOpacity(0.22),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white.withOpacity(0.10)),
                  ),
                  child: const Icon(
                    Icons.add_rounded,
                    color: Colors.white,
                    size: 34,
                  ),
                ),
              ),

              const SizedBox(height: 14),

              const Center(
                child: Text(
                  'Add a New Device',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                    color: Colors.white,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),

              const SizedBox(height: 6),

              Center(
                child: Text(
                  'Follow the steps below to add a new device to your account.',
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    color: Colors.white.withOpacity(0.70),
                  ),
                  textAlign: TextAlign.center,
                ),
              ),

              const SizedBox(height: 18),

              // ===== Steps =====
              const _StepCard(
                step: 1,
                title: 'Choose Device Type',
                description:
                    'Select whether the device is a production device or a consumption device.',
              ),
              const SizedBox(height: 10),
              const _StepCard(
                step: 2,
                title: 'Enter Device Name',
                description:
                    'Write a clear name so you can easily recognize the device later.',
              ),
              const SizedBox(height: 10),
              const _StepCard(
                step: 3,
                title: 'Complete Device Details',
                description:
                    'Fill in any required details such as room or panel capacity based on the device type.',
              ),
              const SizedBox(height: 10),
              const _StepCard(
                step: 4,
                title: 'Save Device',
                description:
                    'Save the device so it appears in your device management list.',
              ),

              const SizedBox(height: 18),

              // ===== Buttons =====
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _loading ? null : _openSetupAndSave,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.button,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                  child: _loading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text(
                          'Continue Setup',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                ),
              ),

              const SizedBox(height: 10),

              SizedBox(
                width: double.infinity,
                height: 52,
                child: OutlinedButton(
                  onPressed: () => Navigator.pop(context),
                  style: OutlinedButton.styleFrom(
                    side: BorderSide(color: Colors.white.withOpacity(0.18)),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                    backgroundColor: Colors.white.withOpacity(0.04),
                  ),
                  child: Text(
                    'Cancel',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.88),
                      fontSize: 14.5,
                      fontWeight: FontWeight.w800,
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

class _StepCard extends StatelessWidget {
  final int step;
  final String title;
  final String description;

  const _StepCard({
    required this.step,
    required this.title,
    required this.description,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      radius: 18,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      child: Row(
        children: [
          // Step number (left)
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: AppColors.mint.withOpacity(0.22),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.12)),
            ),
            child: Center(
              child: Text(
                '$step',
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w900,
                  color: Colors.white,
                ),
              ),
            ),
          ),

          const SizedBox(width: 12),

          // Text
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  description,
                  style: TextStyle(
                    fontSize: 12,
                    height: 1.35,
                    fontWeight: FontWeight.w600,
                    color: Colors.white.withOpacity(0.70),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
