"""Estrutura para manutenção preditiva e futura adoção de Machine Learning.

``build_features`` gera um conjunto de variáveis por ativo (idade, falhas, MTTR,
alertas de sensores...). Hoje o risco é calculado por ``BaselineRiskModel``
(regras ponderadas). Para usar ML, treine um modelo com o dataset exportado em
``/api/intelligence/export/ml_features.csv`` (ex.: scikit-learn), salve-o com
``joblib`` e implemente ``SklearnRiskModel`` — a interface ``predict`` é a mesma.
"""
from datetime import date, datetime, timedelta

from ..models import Asset, Sensor, SensorReading

FEATURE_NAMES = [
    "age_ratio",            # idade / vida útil
    "failures_365d",        # falhas corretivas/emergenciais no último ano
    "failures_90d",
    "mttr_hours",
    "days_since_last_failure",
    "days_since_last_preventive",
    "criticality_weight",
    "sensor_alerts_7d",
]

CRITICALITY_WEIGHT = {"Baixa": 0.25, "Média": 0.5, "Alta": 0.75, "Crítica": 1.0}


def build_features(asset, today=None):
    today = today or date.today()
    now = datetime.combine(today, datetime.max.time())
    tickets = asset.tickets.all()
    failures = [t for t in tickets if t.maintenance_type in ("Corretiva", "Emergencial")]
    f365 = [t for t in failures if t.created_at >= now - timedelta(days=365)]
    f90 = [t for t in failures if t.created_at >= now - timedelta(days=90)]
    repairs = [t.resolution_hours for t in failures if t.resolution_hours is not None]
    last_failure = max((t.created_at for t in failures), default=None)
    prevs = [t.finished_at for t in tickets
             if t.maintenance_type in ("Preventiva", "Calibração", "Inspeção") and t.finished_at]
    last_prev = max(prevs, default=None)
    dep = asset.depreciation(today)
    life = asset.useful_life_years or 10
    alerts = 0
    for sensor in Sensor.query.filter_by(asset_id=asset.id).all():
        readings = SensorReading.query.filter(SensorReading.sensor_id == sensor.id,
                                              SensorReading.recorded_at >= now - timedelta(days=7)).all()
        alerts += sum(1 for r in readings
                      if (sensor.max_value is not None and r.value > sensor.max_value)
                      or (sensor.min_value is not None and r.value < sensor.min_value))
    return {
        "age_ratio": round(dep["age_years"] / life, 3) if life else 0,
        "failures_365d": len(f365),
        "failures_90d": len(f90),
        "mttr_hours": round(sum(repairs) / len(repairs), 1) if repairs else 0,
        "days_since_last_failure": (today - last_failure.date()).days if last_failure else 999,
        "days_since_last_preventive": (today - last_prev.date()).days if last_prev else 999,
        "criticality_weight": CRITICALITY_WEIGHT.get(asset.criticality, 0.5),
        "sensor_alerts_7d": alerts,
    }


class BaselineRiskModel:
    """Modelo heurístico (0-100). Substituível por um modelo treinado."""

    name = "baseline-heuristico-v1"

    def predict(self, x):
        score = 0.0
        score += min(x["age_ratio"], 1.2) * 25
        score += min(x["failures_365d"], 6) * 5
        score += min(x["failures_90d"], 3) * 5
        score += min(x["mttr_hours"], 48) / 48 * 10
        score += 10 if x["days_since_last_failure"] < 30 else 0
        score += 10 if x["days_since_last_preventive"] > 180 else 0
        score += min(x["sensor_alerts_7d"], 10) * 1.5
        score *= 0.6 + 0.6 * x["criticality_weight"]
        return round(min(100.0, score), 1)


def get_model():
    return BaselineRiskModel()


def risk_level(score):
    if score >= 60:
        return "Alto"
    if score >= 35:
        return "Médio"
    return "Baixo"


def recommendation(x, level):
    if level == "Alto":
        if x["sensor_alerts_7d"]:
            return "Inspeção imediata: sensores fora da faixa nos últimos 7 dias"
        if x["age_ratio"] >= 1:
            return "Avaliar substituição: ativo além da vida útil"
        return "Antecipar manutenção preventiva e investigar causa raiz das falhas"
    if level == "Médio":
        return "Acompanhar: revisar plano preventivo e histórico de falhas"
    return "Manter plano preventivo atual"


def predictive_ranking(limit=25):
    model = get_model()
    rows = []
    for asset in Asset.query.filter(Asset.status != "Desativado").all():
        x = build_features(asset)
        score = model.predict(x)
        level = risk_level(score)
        rows.append({"asset_id": asset.id, "tag": asset.tag, "name": asset.name, "category": asset.category,
                     "sector": asset.sector.name if asset.sector else None, "criticality": asset.criticality,
                     "status": asset.status, "score": score, "level": level, "features": x,
                     "recommendation": recommendation(x, level)})
    rows.sort(key=lambda r: -r["score"])
    return {"model": model.name, "features": FEATURE_NAMES, "assets": rows[:limit]}


def feature_dataset():
    """Dataset (uma linha por ativo) para treino de modelos / BI."""
    out = []
    for asset in Asset.query.all():
        x = build_features(asset)
        out.append({"asset_id": asset.id, "tag": asset.tag, "category": asset.category,
                    "criticality": asset.criticality, **x,
                    "label_failed_next_90d": ""})  # rótulo a ser preenchido no treino histórico
    return out

