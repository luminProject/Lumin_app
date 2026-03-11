class UserModel {
  final String username;
  final String phoneNumber;
  final String? avatarUrl;
  final String energySource;
  final bool? hasSolarPanels;
  final double? latitude;
  final double? longitude;

  const UserModel({
    required this.username,
    required this.phoneNumber,
    required this.energySource,
    this.avatarUrl,
    this.hasSolarPanels,
    this.latitude,
    this.longitude,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    final avatar = (json['avatar_url'] ?? '').toString().trim();

    final lat = json['latitude'];
    final lon = json['longitude'];

    String energy = (json['energy_source'] ?? 'Grid only').toString().trim();
    if (energy.isEmpty) energy = 'Grid only';

    final hasSolarPanels = json['has_solar_panels'] is bool
        ? json['has_solar_panels'] as bool
        : null;

    return UserModel(
      username: (json['username'] ?? '').toString().trim(),
      phoneNumber: (json['phone_number'] ?? '').toString().trim(),
      avatarUrl: avatar.isEmpty ? null : avatar,
      energySource: energy,
      hasSolarPanels: hasSolarPanels,
      latitude: (lat is num) ? lat.toDouble() : null,
      longitude: (lon is num) ? lon.toDouble() : null,
    );
  }

  Map<String, dynamic> toUpdateJson() {
    return {
      'username': username.trim(),
      'phone_number': phoneNumber.trim(),
      'energy_source': energySource.trim(),
      'has_solar_panels':
          energySource == 'Grid + Solar' ? hasSolarPanels : null,
      'latitude': latitude,
      'longitude': longitude,
    };
  }

  UserModel copyWith({
    String? username,
    String? phoneNumber,
    String? avatarUrl,
    String? energySource,
    bool? hasSolarPanels,
    double? latitude,
    double? longitude,
    bool clearHasSolarPanels = false,
  }) {
    return UserModel(
      username: username ?? this.username,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      energySource: energySource ?? this.energySource,
      hasSolarPanels:
          clearHasSolarPanels ? null : (hasSolarPanels ?? this.hasSolarPanels),
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
    );
  }
}