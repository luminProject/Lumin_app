import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';
import 'package:lumin_application/Screens/devices/device_success_page.dart';

class DeviceSetupPage extends StatefulWidget {
  final String deviceId;

  const DeviceSetupPage({
    super.key,
    required this.deviceId,
  });

  @override
  State<DeviceSetupPage> createState() => _DeviceSetupPageState();
}

class _DeviceSetupPageState extends State<DeviceSetupPage> {
  final TextEditingController _nameCtrl = TextEditingController();

  final List<String> _rooms = ['Living Room', 'Kitchen', 'Bedroom', 'Bathroom'];
  String? _selectedRoom;

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  // نفس ستايل حق input في اللوقن (تقريبًا) بدون GlassCard
  InputDecoration _inputDecoration({
    required String hint,
    Widget? prefixIcon,
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(color: Colors.white.withOpacity(0.45), fontWeight: FontWeight.w700),
      prefixIcon: prefixIcon,
      suffixIcon: suffixIcon,
      filled: true,
      fillColor: Colors.white.withOpacity(0.05),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: BorderSide(color: Colors.white.withOpacity(0.12)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: BorderSide(color: Colors.white.withOpacity(0.12)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: BorderSide(color: AppColors.mint.withOpacity(0.60), width: 1.2),
      ),
    );
  }

  // ✅ Glass dialog (بدل AlertDialog)
  Future<void> _addRoomDialog() async {
    final ctrl = TextEditingController();

    final added = await showGeneralDialog<String>(
      context: context,
      barrierLabel: 'Add room',
      barrierDismissible: true,
      barrierColor: Colors.black.withOpacity(0.45),
      transitionDuration: const Duration(milliseconds: 220),
      pageBuilder: (_, __, ___) {
        return Center(
          child: _GlassDialog(
            title: 'Add room',
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _GlassTextField(
                  controller: ctrl,
                  hintText: 'e.g., Office',
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: _GlassButton(
                        text: 'Cancel',
                        filled: false,
                        onPressed: () => Navigator.pop(context),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _GlassButton(
                        text: 'Add',
                        filled: true,
                        onPressed: () {
                          final v = ctrl.text.trim();
                          if (v.isEmpty) return;
                          Navigator.pop(context, v);
                        },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
      transitionBuilder: (_, anim, __, child) {
        final curve = Curves.easeOutCubic.transform(anim.value);
        return Transform.scale(
          scale: 0.96 + (0.04 * curve),
          child: Opacity(opacity: curve, child: child),
        );
      },
    );

    if (added != null && added.trim().isNotEmpty) {
      setState(() {
        _rooms.insert(0, added.trim());
        _selectedRoom = added.trim();
      });
    }
  }

void _finishSetup() {
  final deviceName = _nameCtrl.text.trim().isEmpty ? widget.deviceId : _nameCtrl.text.trim();

  Navigator.push(
    context,
    MaterialPageRoute(
      builder: (_) => DeviceSuccessPage(deviceName: deviceName),
    ),
  );
}


  @override
  Widget build(BuildContext context) {
    final canFinish = (_selectedRoom != null) && _nameCtrl.text.trim().isNotEmpty;

    return GradientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        extendBody: true,
        extendBodyBehindAppBar: true,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          centerTitle: true,
          title: const Text('Device Setup', style: TextStyle(fontWeight: FontWeight.w900)),
          leading: IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          ),
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 52),

                // ===== Selected device card =====
                GlassCard(
                  radius: 18,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                  child: Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: AppColors.mint.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.white12),
                        ),
                        child: const Icon(Icons.link_rounded, color: AppColors.mint, size: 22),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Selected device',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.65),
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              widget.deviceId,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 15,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 18),

                // ===== Choose room =====
                const Text(
                  'Choose a room',
                  style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 6),
                Text(
                  'Select the room where this device is located to manage it later.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    height: 1.3,
                  ),
                ),
                const SizedBox(height: 10),

                // ===== Choose room field (NO GlassCard behind it) =====
                Row(
                  children: [
                    // Add room button (left)
                    SizedBox(
                      width: 46,
                      height: 46,
                      child: InkWell(
                        onTap: _addRoomDialog,
                        borderRadius: BorderRadius.circular(14),
                        child: Container(
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.06),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: Colors.white12),
                          ),
                          child: const Icon(Icons.add_rounded, color: Colors.white70),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),

                    // Dropdown field (login vibe)
                    Expanded(
                      child: Container(
                        height: 46,
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.04),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: Colors.white.withOpacity(0.10)),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<String>(
                            value: _selectedRoom,
                            isExpanded: true,
                            elevation: 0,
                            dropdownColor: const Color(0xFF071821),
                            borderRadius: BorderRadius.circular(14),
                            icon: const Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white70),
                            hint: Text(
                              'Select from list',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.55),
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            items: _rooms.map((r) {
                              return DropdownMenuItem<String>(
                                value: r,
                                child: Text(
                                  r,
                                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
                                ),
                              );
                            }).toList(),
                            onChanged: (v) => setState(() => _selectedRoom = v),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 18),

                // ===== Device name =====
                const Text(
                  'Device name',
                  style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 6),
                Text(
                  'Give it a clear name so it is easy to recognize later.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    height: 1.3,
                  ),
                ),
                const SizedBox(height: 10),

                TextField(
                  controller: _nameCtrl,
                  onChanged: (_) => setState(() {}),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
                  decoration: _inputDecoration(hint: 'Example: Living Room AC'),
                ),

                const SizedBox(height: 18),

                // ===== Buttons =====
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton(
                    onPressed: canFinish ? _finishSetup : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.button,
                      disabledBackgroundColor: AppColors.button.withOpacity(0.28),
                      elevation: 0,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    ),
                    child: const Text(
                      'Finish setup',
                      style: TextStyle(fontSize: 15.5, fontWeight: FontWeight.w900),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(color: Colors.white.withOpacity(0.18)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
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

                const SizedBox(height: 18),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ===== Glass dialog widgets =====

class _GlassDialog extends StatelessWidget {
  final String title;
  final Widget child;

  const _GlassDialog({
    required this.title,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Material( // ✅ مهم: يعطي Material ancestor للـ TextField وغيره
      type: MaterialType.transparency,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 18),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
            child: Container(
              width: double.infinity,
              constraints: const BoxConstraints(maxWidth: 360),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.white12),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      fontSize: 18,
                    ),
                  ),
                  const SizedBox(height: 14),
                  child,
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _GlassTextField extends StatelessWidget {
  final TextEditingController controller;
  final String hintText;

  const _GlassTextField({
    required this.controller,
    required this.hintText,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white12),
      ),
      child: TextField(
        controller: controller,
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
        cursorColor: AppColors.mint,
        decoration: InputDecoration(
          hintText: hintText,
          hintStyle: TextStyle(color: Colors.white.withOpacity(0.45)),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        ),
      ),
    );
  }
}

class _GlassButton extends StatelessWidget {
  final String text;
  final bool filled;
  final VoidCallback onPressed;

  const _GlassButton({
    required this.text,
    required this.filled,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: filled ? AppColors.button : Colors.white.withOpacity(0.06),
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          side: filled ? BorderSide.none : BorderSide(color: Colors.white12),
        ),
        child: Text(
          text,
          style: TextStyle(
            color: Colors.white.withOpacity(0.92),
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
    );
  }
}
