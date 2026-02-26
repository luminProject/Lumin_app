import 'device.dart';

class ProductionDevice extends Device {
  double productionKwh;

  ProductionDevice({
    required super.deviceId,
    required super.deviceName,
    required super.deviceType,
    required super.installationDate,
    required super.userId,
    required this.productionKwh,
  });

  @override
  String getDeviceInfo() {
    return 'Production Device: $deviceName (type: $deviceType), '
        'production: $productionKwh kWh';
  }

  double getProduction() {
    return productionKwh;
  }
}
