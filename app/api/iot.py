"""Monitoramento de equipamentos e utilidades (energia, água, gases).

Gateways IoT enviam leituras para ``POST /api/iot/readings`` com o cabeçalho
``X-API-Key``. Formato: ``{"readings": [{"sensor": "EN-QGBT-01", "value": 182.4,
"recorded_at": "2026-09-25T10:00:00"}]}``. Um conector MQTT/Modbus pode ser
adicionado futuramente reaproveitando ``ingest_readings``.
"""
from datetime import datetime, timedelta

from flask import current_app, jsonify, request

from ..auth import can, current_user, require
from ..extensions import db
from ..models import Sensor, SensorReading
from . import bp
from .common import ApiError, apply_fields, get_or_404

SENSOR_FIELDS = {"code": "str", "name": "str", "kind": "str", "unit": "str", "asset_id": "int",
                 "sector_id": "int", "min_value": "float", "max_value": "float", "protocol": "str",
                 "active": "bool"}


def ingest_readings(readings):
    count = 0
    for r in readings:
        sensor = Sensor.query.filter_by(code=r.get("sensor")).first()
        if sensor is None:
            continue
        at = datetime.fromisoformat(r["recorded_at"]) if r.get("recorded_at") else datetime.now()
        value = float(r["value"])
        db.session.add(SensorReading(sensor_id=sensor.id, value=value, recorded_at=at))
        if sensor.last_reading_at is None or at >= sensor.last_reading_at:
            sensor.last_value, sensor.last_reading_at = value, at
        count += 1
    db.session.commit()
    return count


@bp.get("/iot/sensors")
@require("iot.view")
def list_sensors():
    q = Sensor.query
    if request.args.get("kind"):
        q = q.filter_by(kind=request.args["kind"])
    return jsonify([s.to_dict() for s in q.order_by(Sensor.kind, Sensor.code)])


@bp.post("/iot/sensors")
@require("iot.edit")
def create_sensor():
    sensor = apply_fields(Sensor(), request.get_json(silent=True) or {}, SENSOR_FIELDS,
                          required=("code", "name", "kind"))
    db.session.add(sensor)
    db.session.commit()
    return jsonify(sensor.to_dict()), 201


@bp.put("/iot/sensors/<int:sensor_id>")
@require("iot.edit")
def update_sensor(sensor_id):
    sensor = get_or_404(Sensor, sensor_id, "Sensor")
    apply_fields(sensor, request.get_json(silent=True) or {}, SENSOR_FIELDS)
    db.session.commit()
    return jsonify(sensor.to_dict())


@bp.get("/iot/sensors/<int:sensor_id>/readings")
@require("iot.view")
def sensor_readings(sensor_id):
    sensor = get_or_404(Sensor, sensor_id, "Sensor")
    hours = min(24 * 30, int(request.args.get("hours", 24)))
    since = datetime.now() - timedelta(hours=hours)
    rows = (SensorReading.query.filter(SensorReading.sensor_id == sensor.id, SensorReading.recorded_at >= since)
            .order_by(SensorReading.recorded_at).all())
    return jsonify({"sensor": sensor.to_dict(), "readings": [r.to_dict() for r in rows]})


@bp.post("/iot/readings")
def post_readings():
    key = request.headers.get("X-API-Key")
    user = current_user()
    if key != current_app.config["IOT_API_KEY"] and not can(user, "iot.edit"):
        raise ApiError("Chave de API inválida", 401)
    data = request.get_json(silent=True) or {}
    readings = data.get("readings") or ([data] if "sensor" in data else [])
    try:
        count = ingest_readings(readings)
    except (KeyError, TypeError, ValueError):
        raise ApiError("Formato de leitura inválido")
    return jsonify({"ingested": count}), 201


@bp.get("/iot/summary")
@require("iot.view")
def iot_summary():
    """Consumo/leituras das últimas 24h agregados por tipo de sensor."""
    since = datetime.now() - timedelta(hours=24)
    out = {}
    for s in Sensor.query.filter_by(active=True).all():
        values = [r.value for r in SensorReading.query.filter(SensorReading.sensor_id == s.id,
                                                              SensorReading.recorded_at >= since)]
        k = out.setdefault(s.kind, {"kind": s.kind, "sensors": 0, "alerts": 0, "unit": s.unit, "avg": []})
        k["sensors"] += 1
        k["alerts"] += 1 if s.state == "alerta" else 0
        if values:
            k["avg"].append(sum(values) / len(values))
    for k in out.values():
        k["avg"] = round(sum(k["avg"]) / len(k["avg"]), 2) if k["avg"] else None
    return jsonify(list(out.values()))
