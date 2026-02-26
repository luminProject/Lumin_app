import 'package:flutter/material.dart';
import 'package:intl_phone_field/intl_phone_field.dart';

import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';

class EditProfilePage extends StatefulWidget {
  const EditProfilePage({super.key});

  @override
  State<EditProfilePage> createState() => _EditProfilePageState();
}

class _EditProfilePageState extends State<EditProfilePage> {
  final _nameCtrl = TextEditingController(text: 'John Doe');

  // نخزن الرقم النهائي هنا (مثلاً +9665xxxxxxx)
  String _fullPhone = '+1 (555) 123-4567';

  String? _city;

  final _cities = const [
    'Jeddah',
    'Riyadh',
    'Makkah',
    'Madinah',
    'Dammam',
  ];

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: true,
        title: 'Edit Profile',
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
        ),
        actions: const [],

        // ✅ تبقى على profile tab
        bottomNavigationBar: const HomeBottomNav(currentIndex: 4),

        child: Column(
          children: [
            const SizedBox(height:125),

            // ===== Avatar =====
            _avatarSection(),

            const SizedBox(height: 14),

            // ===== Form Card =====
            GlassCard(
              radius: 20,
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _label('Full Name'),
                  const SizedBox(height: 8),
                  _underlineField(
                    controller: _nameCtrl,
                    hint: 'Full Name',
                    keyboardType: TextInputType.name,
                  ),

                  const SizedBox(height: 16),

                  // ✅ Phone with flag + country code
                  _label('Phone Number'),
                  const SizedBox(height: 8),
                  _phoneIntlField(),

                  const SizedBox(height: 16),


                  // Button
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton(
                      onPressed: () {
                        final name = _nameCtrl.text.trim();
                        final phone = _fullPhone;
                        

                        // TODO: Save changes logic
                        // مثال:
                        // print('name=$name, phone=$phone, city=$city');
                      },
                      child: const Text(
                        'Save Changes',
                        style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w900),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _avatarSection() {
    return Column(
      children: [
        Stack(
          clipBehavior: Clip.none,
          children: [
            Container(
              width: 86,
              height: 86,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.mint, width: 2),
              ),
              child: ClipOval(
                child: Image.network(
                  'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400',
                  fit: BoxFit.cover,
                ),
              ),
            ),
            Positioned(
              bottom: -2,
              right: -2,
              child: Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color: AppColors.mint,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.black.withOpacity(0.15), width: 2),
                ),
                child: const Icon(Icons.photo_camera_rounded, size: 16, color: Colors.white),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Change profile photo',
          style: TextStyle(
            color: Colors.white.withOpacity(0.65),
            fontSize: 11.5,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _label(String text) {
    return Text(
      text,
      style: TextStyle(
        color: Colors.white.withOpacity(0.72),
        fontSize: 16,
        fontWeight: FontWeight.w700,
      ),
    );
  }

  // TextField ستايله underline مثل الصورة
  Widget _underlineField({
    required TextEditingController controller,
    required String hint,
    required TextInputType keyboardType,
  }) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
      cursorColor: AppColors.mint,
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.35)),
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(vertical: 10),
        enabledBorder: UnderlineInputBorder(
          borderSide: BorderSide(color: Colors.white.withOpacity(0.18)),
        ),
        focusedBorder: const UnderlineInputBorder(
          borderSide: BorderSide(color: AppColors.mint, width: 1.4),
        ),
      ),
    );
  }

  // ✅ Phone field مع علم + كود الدولة
  Widget _phoneIntlField() {
    return IntlPhoneField(
      initialCountryCode: 'SA', // تقدرين تغيرينها
      disableLengthCheck: true,
      cursorColor: AppColors.mint,

      // النص داخل الحقل
      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),

      // نص dropdown (الكود + البلد)
      dropdownTextStyle: TextStyle(
        color: Colors.white.withOpacity(0.88),
        fontWeight: FontWeight.w800,
      ),
      dropdownIcon: Icon(
        Icons.keyboard_arrow_down_rounded,
        color: Colors.white.withOpacity(0.65),
      ),

      decoration: InputDecoration(
        hintText: 'Phone Number',
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.35)),
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(vertical: 10),
        enabledBorder: UnderlineInputBorder(
          borderSide: BorderSide(color: Colors.white.withOpacity(0.18)),
        ),
        focusedBorder: const UnderlineInputBorder(
          borderSide: BorderSide(color: AppColors.mint, width: 1.4),
        ),
      ),

      onChanged: (phone) {
        // +9665xxxxxxx
        _fullPhone = phone.completeNumber;
      },
    );
  }

  Widget _dropdownUnderline() {
    return Container(
      padding: const EdgeInsets.only(bottom: 6),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: Colors.white.withOpacity(0.18)),
        ),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: _city,
          isExpanded: true,
          icon: Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white.withOpacity(0.65)),
          dropdownColor: const Color(0xFF0E2B2E),
          borderRadius: BorderRadius.circular(12),
          hint: Text(
            'Select your city',
            style: TextStyle(color: Colors.white.withOpacity(0.35), fontWeight: FontWeight.w700),
          ),
          items: _cities
              .map(
                (c) => DropdownMenuItem<String>(
                  value: c,
                  child: Text(
                    c,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
                  ),
                ),
              )
              .toList(),
          onChanged: (v) => setState(() => _city = v),
        ),
      ),
    );
  }
}
