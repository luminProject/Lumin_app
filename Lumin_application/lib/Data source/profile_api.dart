import 'package:supabase_flutter/supabase_flutter.dart';

import '../services/api_service.dart';
import '../Classes/user_model.dart';

class ProfileApi {
  final ApiService _api;
  ProfileApi(this._api);

  String _uid() {
    final id = Supabase.instance.client.auth.currentUser?.id;
    if (id == null) throw Exception('Not logged in');
    return id;
  }

  Future<UserModel> getMyProfile() async {
    final data = await _api.getProfile(_uid());
    return UserModel.fromJson(data);
  }

  Future<void> updateMyProfile(UserModel model) async {
    await _api.updateProfile(_uid(), model.toUpdateJson());
  }

  Future<void> updateMyAvatar(String avatarUrl) async {
    await _api.updateAvatarUrl(_uid(), avatarUrl);
  }
}