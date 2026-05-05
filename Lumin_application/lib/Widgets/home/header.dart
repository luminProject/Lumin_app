import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:lumin_application/Recomendation/notificationspage.dart';
import '../../theme/app_colors.dart';

class HomeHeader extends StatefulWidget {
  const HomeHeader({super.key});

  @override
  State<HomeHeader> createState() => _HomeHeaderState();
}

class _HomeHeaderState extends State<HomeHeader> {
  String _displayName = '';
  String? _avatarUrl;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Reload profile every time this widget becomes visible
    // (e.g. after returning from EditProfilePage)
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final userId = Supabase.instance.client.auth.currentUser?.id;
      if (userId == null) return;

      final res = await Supabase.instance.client
          .from('users')
          .select('username, avatar_url')
          .eq('user_id', userId)
          .maybeSingle();

      if (!mounted || res == null) return;

      final username = res['username'] as String?;
      setState(() {
        _displayName = (username != null && username.isNotEmpty)
            ? username.split(' ').first
            : (Supabase.instance.client.auth.currentUser?.email ?? '').split('@').first;
        _avatarUrl = res['avatar_url'] as String?;
      });
    } catch (_) {}
  }

  String get _todayFormatted =>
      DateFormat('EEEE, d MMMM yyyy').format(DateTime.now());

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        CircleAvatar(
          radius: 18,
          backgroundColor: Colors.white24,
          backgroundImage: (_avatarUrl != null && _avatarUrl!.isNotEmpty)
              ? NetworkImage(_avatarUrl!)
              : null,
          child: (_avatarUrl == null || _avatarUrl!.isEmpty)
              ? const Icon(Icons.person, size: 18, color: Colors.white54)
              : null,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Hello ${_displayName.isNotEmpty ? _displayName : '...'}',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 2),
              Text(
                _todayFormatted,
                style: const TextStyle(fontSize: 12, color: AppColors.sub),
              ),
            ],
          ),
        ),
        IconButton(
          onPressed: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const NotificationsPage()),
            );
          },
          icon: const Icon(Icons.notifications_none_rounded, color: AppColors.mint),
        ),
      ],
    );
  }
}