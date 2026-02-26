import 'package:flutter/material.dart';
import 'package:lumin_application/Recomendation/notificationspage.dart';
import '../../theme/app_colors.dart';

class HomeHeader extends StatelessWidget {
  const HomeHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const CircleAvatar(radius: 18, backgroundColor: Colors.white24),
        const SizedBox(width: 10),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Hello Imran', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
              SizedBox(height: 2),
              Text('Thursday, 06 August 2025', style: TextStyle(fontSize: 12, color: AppColors.sub)),
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
