import 'package:flutter/material.dart';
import 'package:lumin_application/Recomendation/notificationspage.dart';
import 'package:lumin_application/Screens/profile%20settings%20page/about_lumin_page.dart';
import 'package:lumin_application/Screens/profile%20settings%20page/change_password_page.dart';
import 'package:lumin_application/Screens/profile%20settings%20page/edit_profile_page.dart';
import 'package:lumin_application/Screens/profile%20settings%20page/privacy_page.dart';
import 'package:lumin_application/Screens/login.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class ProfileSettingsPage extends StatelessWidget {
  const ProfileSettingsPage({super.key});

  void _showLogoutDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (dialogCtx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF0F2A33),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          title: const Text(
            'Confirm Logout',
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
          content: const Text(
            'Are you sure you want to log out?',
            style: TextStyle(
              color: Colors.white70,
              fontWeight: FontWeight.w600,
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogCtx),
              child: const Text(
                'No',
                style: TextStyle(
                  color: Colors.grey,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.redAccent,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: () async {
                await Supabase.instance.client.auth.signOut();

                if (!dialogCtx.mounted) return;

                Navigator.pop(dialogCtx);

                Navigator.of(context).pushAndRemoveUntil(
                  MaterialPageRoute(builder: (_) => const LoginPage()),
                  (route) => false,
                );
              },
              child: const Text(
                'Yes',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: true,
        title: 'Settings',
        leading: const SizedBox(width: 48),

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

        bottomNavigationBar: const HomeBottomNav(currentIndex: 4),

        child: Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Column(
            children: [
              const SizedBox(height: 45),

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
                },
              ),

              const SizedBox(height: 25),

              // 🔴 Logout Tile (Red)
              _settingsTile(
                context,
                icon: Icons.logout_rounded,
                title: 'Log Out',
                isLogout: true,
                onTap: () => _showLogoutDialog(context),
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
    bool isLogout = false,
  }) {
    final Color iconColor =
        isLogout ? Colors.redAccent : AppColors.mint;

    final Color bgColor =
        isLogout ? Colors.redAccent.withOpacity(0.15) : AppColors.mint.withOpacity(0.18);

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
                color: bgColor,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: iconColor, size: 20),
            ),
            const SizedBox(width: 15),
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  color: isLogout ? Colors.redAccent : Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: iconColor,
              size: 26,
            ),
          ],
        ),
      ),
    );
  }
}