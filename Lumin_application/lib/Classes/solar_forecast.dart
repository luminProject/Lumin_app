import 'forcast_model.dart';

class SolarForecast {
  int forecast_id;
  double predicted_production_kwh;
  double confidence_level;
  ForcastModel model;

  SolarForecast({
    required this.forecast_id,
    required this.predicted_production_kwh,
    required this.confidence_level,
    required this.model,
  });

  void generateForecast() {}
  void trainModel() {}
  double getResult() => predicted_production_kwh;
}