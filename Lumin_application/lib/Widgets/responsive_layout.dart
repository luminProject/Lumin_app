import 'package:flutter/material.dart';

class ResponsiveLayout extends StatelessWidget {
  final Widget child;

  // AppBar options
  final bool showAppBar;
  final String? title;
  final Widget? leading;
  final List<Widget>? actions;

  // Bottom nav (optional)
  final Widget? bottomNavigationBar;

  const ResponsiveLayout({
    super.key,
    required this.child,
    this.showAppBar = false,
    this.title,
    this.leading,
    this.actions,
    this.bottomNavigationBar,
  });

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final bool isMobile = size.width < 600;

    return Scaffold(
      backgroundColor: Colors.transparent,
      extendBodyBehindAppBar: false,

      appBar: showAppBar
          ? AppBar(
              leading: leading,
              title: Text(
                title ?? '',
                style: const TextStyle(
                  fontSize: 25,
                  fontWeight: FontWeight.w900,
                ),
              ),
              centerTitle: true,
              actions: actions,
              backgroundColor: Colors.transparent,
              elevation: 0,
              scrolledUnderElevation: 0,
            )
          : null,

      bottomNavigationBar: bottomNavigationBar,

      // ✅ بدل Center عشان ما يوسّط المحتوى ويعمل فراغ فوق
      body: Align(
        alignment: Alignment.topCenter,
        child: SingleChildScrollView(
          child: Container(
            width: double.infinity,
            constraints: const BoxConstraints(maxWidth: 1200),
            padding: EdgeInsets.symmetric(
              horizontal: isMobile ? 16.0 : size.width * 0.15,
              vertical: 16.0,
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}