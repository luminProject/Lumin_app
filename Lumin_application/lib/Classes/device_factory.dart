import 'consumption_device.dart';
import 'device.dart';
import 'production_device.dart';

class DeviceFactory {
  Device createDevice({
    required String name,
    required String type,
    required int deviceId,
    required int userId,
    DateTime? installationDate,
    double initialKwh = 0,
    double powerRating = 0,
  }) {
    final installedAt = installationDate ?? DateTime.now();

    switch (type.toLowerCase()) {
      case 'consumption':
        return ConsumptionDevice(
          deviceId: deviceId,
          deviceName: name,
          deviceType: type,
          installationDate: installedAt,
          userId: userId,
          consumptionKwh: initialKwh,
          powerRating: powerRating,
        );
      case 'production':
        return ProductionDevice(
          deviceId: deviceId,
          deviceName: name,
          deviceType: type,
          installationDate: installedAt,
          userId: userId,
          productionKwh: initialKwh,
        );
      default:
        throw ArgumentError('Unknown device type: $type');
    }
  }
}
