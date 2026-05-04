import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/theme/app_colors.dart';

class DeviceSetupPage extends StatefulWidget {
  final String deviceId;
  final bool isEditMode;
  final int? deviceDbId;
  final String? initialName;
  final String? initialRoom;
  final String? initialDeviceType;
  final String? initialPanelCapacity;
  final bool initialIsShiftable;

  const DeviceSetupPage({
    super.key,
    required this.deviceId,
    this.isEditMode = false,
    this.deviceDbId,
    this.initialName,
    this.initialRoom,
    this.initialDeviceType,
    this.initialPanelCapacity,
    this.initialIsShiftable = false,
  });

  @override
  State<DeviceSetupPage> createState() => _DeviceSetupPageState();
}

class _DeviceSetupPageState extends State<DeviceSetupPage> {
  final TextEditingController _nameCtrl = TextEditingController();
  final TextEditingController _capacityCtrl = TextEditingController();

  final List<String> _rooms = ['Living Room', 'Kitchen', 'Bedroom', 'Bathroom'];

  String? _selectedRoom;
  String _deviceType = 'consumption';
  bool _isShiftable = false;

  @override
  void initState() {
    super.initState();
    _nameCtrl.text = widget.initialName ?? '';
    _capacityCtrl.text = widget.initialPanelCapacity ?? '';
    _selectedRoom = widget.initialRoom;
    _deviceType = widget.initialDeviceType ?? 'consumption';
    _isShiftable = _deviceType == 'consumption'
        ? widget.initialIsShiftable
        : false;
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _capacityCtrl.dispose();
    super.dispose();
  }

  InputDecoration _inputDecoration({
    required String hint,
    Widget? prefixIcon,
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(
        color: Colors.white.withOpacity(0.45),
        fontWeight: FontWeight.w700,
      ),
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
        borderSide: BorderSide(
          color: AppColors.mint.withOpacity(0.60),
          width: 1.2,
        ),
      ),
    );
  }

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
                _GlassTextField(controller: ctrl, hintText: 'e.g., Office'),
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
    final bool isSolarPanel = _deviceType == 'production';
    final deviceName = _nameCtrl.text.trim();

    final payload = {
      "device_id": widget.deviceDbId,
      "device_name": deviceName,
      "device_type": _deviceType,
      "room": _deviceType == 'production' ? null : _selectedRoom,
      "panel_capacity": isSolarPanel ? _capacityCtrl.text.trim() : null,
      "is_shiftable": _deviceType == 'consumption' ? _isShiftable : false,
    };

    if (!widget.isEditMode) {
      payload["created_at"] = DateTime.now().toIso8601String();
    }

    Navigator.pop(context, payload);
  }

  @override
  Widget build(BuildContext context) {
    final bool isSolarPanel = _deviceType == 'production';
    final canFinish = _deviceType == 'production'
        ? _nameCtrl.text.trim().isNotEmpty
        : (_selectedRoom != null && _nameCtrl.text.trim().isNotEmpty);

    return GradientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        extendBody: true,
        extendBodyBehindAppBar: true,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          centerTitle: true,
          title: Text(
            widget.isEditMode ? 'Device Settings' : 'Device Setup',
            style: const TextStyle(fontWeight: FontWeight.w900),
          ),
          leading: IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(
              Icons.arrow_back_ios_new_rounded,
              color: Colors.white,
            ),
          ),
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 52),

                const Text(
                  'Device type',
                  style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 6),
                Text(
                  widget.isEditMode
                      ? 'Device type cannot be changed here.'
                      : 'Choose whether this device consumes energy or produces it.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    height: 1.3,
                  ),
                ),
                const SizedBox(height: 10),

                Row(
                  children: [
                    Expanded(
                      child: InkWell(
                        onTap: widget.isEditMode
                            ? null
                            : () => setState(() => _deviceType = 'consumption'),
                        borderRadius: BorderRadius.circular(14),
                        child: Container(
                          height: 52,
                          decoration: BoxDecoration(
                            color: _deviceType == 'consumption'
                                ? AppColors.button.withOpacity(0.18)
                                : Colors.white.withOpacity(0.04),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: _deviceType == 'consumption'
                                  ? AppColors.mint.withOpacity(0.70)
                                  : Colors.white.withOpacity(0.10),
                            ),
                          ),
                          child: const Center(
                            child: Text(
                              'Consumption',
                              style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: InkWell(
                        onTap: widget.isEditMode
                            ? null
                            : () => setState(() {
                                _deviceType = 'production';
                                _isShiftable = false;
                              }),
                        borderRadius: BorderRadius.circular(14),
                        child: Container(
                          height: 52,
                          decoration: BoxDecoration(
                            color: _deviceType == 'production'
                                ? AppColors.button.withOpacity(0.18)
                                : Colors.white.withOpacity(0.04),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: _deviceType == 'production'
                                  ? AppColors.mint.withOpacity(0.70)
                                  : Colors.white.withOpacity(0.10),
                            ),
                          ),
                          child: const Center(
                            child: Text(
                              'Production',
                              style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 18),

                if (!isSolarPanel) ...[
                  const Text(
                    'Choose a room',
                    style: TextStyle(
                      fontSize: 14.5,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    widget.isEditMode
                        ? 'Update the room where this device is located.'
                        : 'Select the room where this device is located to manage it later.',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.65),
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      height: 1.3,
                    ),
                  ),
                  const SizedBox(height: 10),

                  Row(
                    children: [
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
                            child: const Icon(
                              Icons.add_rounded,
                              color: Colors.white70,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Container(
                          height: 46,
                          padding: const EdgeInsets.symmetric(horizontal: 14),
                          decoration: BoxDecoration(
                            color: _deviceType == 'production'
                                ? Colors.white.withOpacity(0.02)
                                : Colors.white.withOpacity(0.04),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: Colors.white.withOpacity(0.10),
                            ),
                          ),
                          child: DropdownButtonHideUnderline(
                            child: DropdownButton<String>(
                              value: _selectedRoom,
                              isExpanded: true,
                              elevation: 0,
                              dropdownColor: const Color(0xFF071821),
                              borderRadius: BorderRadius.circular(14),
                              icon: const Icon(
                                Icons.keyboard_arrow_down_rounded,
                                color: Colors.white70,
                              ),
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
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                );
                              }).toList(),
                              onChanged: _deviceType == 'production'
                                  ? null
                                  : (v) => setState(() {
                                      _selectedRoom = v;
                                    }),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 18),

                  const Text(
                    'Is this device shiftable?',
                    style: TextStyle(
                      fontSize: 14.5,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Can you run this device at any time of day? For example, washing machine or dishwasher.',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.65),
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      height: 1.3,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.04),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: Colors.white.withOpacity(0.10)),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Shiftable device',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w900,
                                  fontSize: 13.5,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Enable this for flexible devices that can be scheduled later.',
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.58),
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w600,
                                  height: 1.25,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Switch(
                          value: _isShiftable,
                          activeColor: AppColors.mint,
                          onChanged: (value) {
                            setState(() {
                              _isShiftable = value;
                            });
                          },
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 18),
                ],

                if (isSolarPanel) ...[
                  const Text(
                    'Panel capacity',
                    style: TextStyle(
                      fontSize: 14.5,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    widget.isEditMode
                        ? 'Update the power capacity of the solar panel.'
                        : 'Enter the power capacity of the solar panel.',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.65),
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      height: 1.3,
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _capacityCtrl,
                    keyboardType: TextInputType.number,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
                    decoration: _inputDecoration(hint: 'Example: 500'),
                  ),
                  const SizedBox(height: 18),
                ],

                const Text(
                  'Device name',
                  style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 6),
                Text(
                  widget.isEditMode
                      ? 'Update the device name here.'
                      : isSolarPanel
                      ? 'Please enter a name for the solar panel device.'
                      : 'Please enter a device name for consumption devices.',
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
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                  decoration: _inputDecoration(
                    hint: isSolarPanel
                        ? 'Example: Solar Panel 1'
                        : 'Example: Living Room AC',
                  ),
                ),

                const SizedBox(height: 18),

                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton(
                    onPressed: canFinish ? _finishSetup : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.button,
                      disabledBackgroundColor: AppColors.button.withOpacity(
                        0.28,
                      ),
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                    child: Text(
                      widget.isEditMode ? 'Save changes' : 'Finish setup',
                      style: const TextStyle(
                        fontSize: 15.5,
                        fontWeight: FontWeight.w900,
                      ),
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
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
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

  const _GlassDialog({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Material(
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

  const _GlassTextField({required this.controller, required this.hintText});

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
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w800,
        ),
        cursorColor: AppColors.mint,
        decoration: InputDecoration(
          hintText: hintText,
          hintStyle: TextStyle(color: Colors.white.withOpacity(0.45)),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 14,
            vertical: 14,
          ),
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
          backgroundColor: filled
              ? AppColors.button
              : Colors.white.withOpacity(0.06),
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
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
