import 'package:flutter/material.dart';
import 'package:lumin_application/Recomendation/notificationspage.dart';
import 'package:lumin_application/Screens/profile%20settings%20page/about_lumin_page.dart';
import 'package:lumin_application/Screens/profile%20settings%20page/change_password_page.dart';
import 'package:lumin_application/Screens/profile%20settings%20page/edit_profile_page.dart';
import 'package:lumin_application/Screens/profile%20settings%20page/privacy_page.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';

class ProfileSettingsPage extends StatelessWidget {
  const ProfileSettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: true,
        title: 'Settings',

        // ✅ بدون زر رجوع
        leading: const SizedBox(width: 48),

        // ✅ (اختياري) جرس مثل باقي الصفحات
        actions: [
          IconButton(
            onPressed: () {
  Navigator.push(
    context,
    MaterialPageRoute(builder: (_) => const NotificationsPage()),
  );
},
            icon: const Icon(
              Icons.notifications_none_rounded,
              color: AppColors.mint,
            ),
          ),
        ],

        // ✅ الصفحة الأخيرة في الناف بار
        bottomNavigationBar: const HomeBottomNav(currentIndex: 4),

        child: Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Column(
            children: [
              const SizedBox(height:125),

              _settingsTile(
                context,
                icon: Icons.person_rounded,
                title: 'Edit Profile',
               onTap: () {
  Navigator.push(
    context,
    MaterialPageRoute(builder: (_) => const EditProfilePage()),
  );
},

              ),
              const SizedBox(height: 15),

              _settingsTile(
                context,
                icon: Icons.lock_rounded,
                title: 'Change Password',
                 onTap: () {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ChangePasswordPage()),
    );
  },
              ),
              const SizedBox(height: 15),

              _settingsTile(
                context,
                icon: Icons.info_rounded,
                title: 'About LUMIN',
                 onTap: () {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const AboutLuminPage()),
    );
  },
              ),
              const SizedBox(height: 15),

              _settingsTile(
                context,
                icon: Icons.privacy_tip_rounded,
                title: 'Privacy',
                onTap: () {
                    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const PrivacyPage()),
    );
                  // TODO: Navigator.push(... PrivacyPage)
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _settingsTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: GlassCard(
        radius: 18,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        child: Row(
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: AppColors.mint.withOpacity(0.18),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: AppColors.mint, size: 20),
            ),
            const SizedBox(width: 15),

            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize:16,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),

            const Icon(
              Icons.chevron_right_rounded,
              color: AppColors.mint,
              size: 26,
            ),
          ],
        ),
      ),
    );
  }
}
