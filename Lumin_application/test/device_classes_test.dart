import 'package:flutter_test/flutter_test.dart';
import 'package:lumin_application/Classes/consumption_device.dart';
import 'package:lumin_application/Classes/device_factory.dart';
import 'package:lumin_application/Classes/observer.dart';
import 'package:lumin_application/Classes/production_device.dart';

class _TestObserver implements Observer {
  int updates = 0;

  @override
  void update(device) {
    updates++;
  }
}

void main() {
  test('DeviceFactory creates a ConsumptionDevice', () {
    final factory = DeviceFactory();

    final device = factory.createDevice(
      name: 'Air Conditioner',
      type: 'consumption',
      deviceId: 1,
      userId: 100,
      initialKwh: 12,
      powerRating: 2.5,
    );

    expect(device, isA<ConsumptionDevice>());
  });

  test('DeviceFactory creates a ProductionDevice', () {
    final factory = DeviceFactory();

    final device = factory.createDevice(
      name: 'Solar Panel',
      type: 'production',
      deviceId: 2,
      userId: 100,
      initialKwh: 25,
    );

    expect(device, isA<ProductionDevice>());
  });

  test('collectSensorData notifies attached observers', () {
    final device = ConsumptionDevice(
      deviceId: 1,
      deviceName: 'Heater',
      deviceType: 'consumption',
      installationDate: DateTime(2026, 1, 1),
      userId: 100,
      consumptionKwh: 0,
      powerRating: 1.2,
    );
    final observer = _TestObserver();

    device.attach(observer);
    device.collectSensorData(4.2);

    expect(device.sensorReadings, hasLength(1));
    expect(observer.updates, 1);
  });
}
