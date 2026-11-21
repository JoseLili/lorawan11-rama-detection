"""Genera las 4 gráficas armónicas (PNG de alta resolución) para la presentación UCLM / Coloquio PCIC.

Lee exclusivamente los archivos CSV oficiales en results/linea_base/ y renderiza las figuras
mediante GDI+ (.NET System.Drawing) con antialiasing y escalas estrictamente uniformes.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results" / "linea_base"
OUT_DIR = ROOT / "docs" / "img" / "coloquio_uclm"
ART_DIR = Path(r"C:\Users\jose_\.gemini\antigravity\brain\69484fbb-153d-4dc8-bbe3-c46870f09661")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def recopilar_datos() -> dict:
    # 1. Curva de operación (rev22 despliegue: p99.9, p99, p98, p95 + rev24 banco p99.9 y p99)
    curva_desp = pd.read_csv(RES / "rev22" / "examen_despliegue" / "curva_operacion.csv")
    curva_vb = curva_desp[curva_desp["detector"] == "Ens-Vb-R"].set_index("nivel")

    m_banco = pd.read_csv(RES / "rev24" / "metricas_banco.csv")
    fa_banco = pd.read_csv(RES / "rev24" / "falsas_alarmas_banco.csv")
    m_rev23 = pd.read_csv(RES / "rev23" / "metricas.csv")
    desp_24 = pd.read_csv(RES / "rev24" / "despliegue_2026.csv")
    sem_d1 = pd.read_csv(RES / "rev23b" / "por_semana.csv")

    # Datos Gráfica 1: Punto de operación (p99.9, p99, p98, p95)
    niveles_op = [0.001, 0.01, 0.02, 0.05]
    nombres_op = ["p99.9", "p99", "p98", "p95"]
    g1_desp = []
    for nv, nom in zip(niveles_op, nombres_op):
        r = curva_vb.loc[nv]
        g1_desp.append({
            "percentil": nom,
            "nivel": nv,
            "dias_fa_nominal": round(nv * 365.0, 1),
            "dias_fa_real": round(float(r["fa_limpia"]) * 365.0, 1),
            "recall_d100": float(r["recall_100"]),
            "recall_d50": float(r["recall_50"]),
            "recall_d20": float(r["recall_20"]),
            "prec_d50": float(r["precision_50"]),
            "Fbar": float(r["Fbar"]),
        })

    # Banco p99.9 vs p99 en todas las magnitudes (% y ppb) para Ens-Vb-X0.2596
    mx = m_banco[(m_banco["detector"] == "Ens-Vb-X0.2596") & (m_banco["escenario"] == "E1")]
    fax = fa_banco[fa_banco["detector"] == "Ens-Vb-X0.2596"].set_index("nivel")
    tams_orden = ["d20", "d50", "d100", "a10", "a20", "a40"]
    g1_banco = {}
    for nv, nom in [(0.001, "p99.9"), (0.01, "p99")]:
        sub = mx[mx["nivel"] == nv].set_index("tamano")
        g1_banco[nom] = {
            "dias_fa_banco": round(float(fax.loc[nv, "fa"]) * 365.0, 1),
            "recall": [float(sub.loc[t, "recall"]) for t in tams_orden],
            "F1": [float(sub.loc[t, "F1"]) for t in tams_orden],
            "precision": [float(sub.loc[t, "precision"]) for t in tams_orden],
        }

    # Datos Gráfica 2: 1 estación atacada (E1) en umbral único p99 (0.01)
    # Detectores: Ensamble vecinal con filtro (Ens-Vb-X0.2596), Ensamble con referencia propia (Ens-V0-R),
    # Regla R3 (R3), PARAAD-SA (PARAAD)
    g2_banco = {}
    for det_key, det_label in [
        ("Ens-Vb-X0.2596", "Ensamble vecinal con filtro (final)"),
        ("Ens-V0-R", "Ensamble con referencia propia"),
        ("R3", "Regla R3 (sin entrenar)"),
        ("PARAAD", "PARAAD-SA"),
    ]:
        src_df = m_banco if det_key in ("Ens-Vb-X0.2596", "PARAAD") else m_rev23
        sub = src_df[(src_df["detector"] == det_key) & (src_df["nivel"] == 0.01) & (src_df["escenario"] == "E1")].set_index("tamano")
        g2_banco[det_key] = {
            "label": det_label,
            "recall": [float(sub.loc[t, "recall"]) for t in tams_orden],
            "F1": [float(sub.loc[t, "F1"]) for t in tams_orden],
            "precision": [float(sub.loc[t, "precision"]) for t in tams_orden],
        }

    # Despliegue ago-sep 2026 a p99 para Ens-Vb-X0.2596
    dx = desp_24[(desp_24["detector"] == "Ens-Vb-X0.2596") & (desp_24["nivel"] == 0.01)].iloc[0]
    g2_desp = {
        "recall": [float(dx["recall_20"]), float(dx["recall_50"]), float(dx["recall_100"])],
        "F1": [float(dx["F1_20"]), float(dx["F1_50"]), float(dx["F1_100"])],
        "precision": [float(dx["precision_20"]), float(dx["precision_50"]), float(dx["precision_100"])],
        "Fbar": float(dx["Fbar"]),
    }

    # Datos Gráfica 3: Ataque coordinado (E1=0, E2-1=1, E2-2=2, E2-4=4 vecinas) a p99
    # Solo Ensamble vecinal con filtro vs PARAAD-SA, mostrando Recall (estación original), Precisión y F1
    esc_map = [("E1", 0), ("E2-1", 1), ("E2-2", 2), ("E2-4", 4)]
    g3 = {}
    for tam in ("d50", "a20"):
        g3[tam] = {}
        for det_key in ("Ens-Vb-X0.2596", "PARAAD"):
            sub = m_banco[(m_banco["detector"] == det_key) & (m_banco["nivel"] == 0.01) & (m_banco["tamano"] == tam)].set_index("escenario")
            g3[tam][det_key] = {
                "x": [ xv for _, xv in esc_map ],
                "recall": [ float(sub.loc[ek, "recall_original"]) for ek, _ in esc_map ],
                "precision": [ float(sub.loc[ek, "precision"]) for ek, _ in esc_map ],
                "F1": [ float(sub.loc[ek, "F1"]) for ek, _ in esc_map ],
            }

    # Datos Gráfica 4: Sesgo sostenido D1 (+20 ppb escalón, semanas 1 a 8, p99)
    sub_d1 = sem_d1[(sem_d1["forma"] == "escalon") & (sem_d1["A"] == 20) & (sem_d1["nivel"] == 0.01)]
    g4 = {}
    for det_key in ("Ens-Vb-X0.2596", "Ens-V0-R", "PARAAD"):
        s = sub_d1[sub_d1["detector"] == det_key].sort_values("semana")
        g4[det_key] = {
            "semanas": [int(x) for x in s["semana"].tolist()],
            "recall": [float(x) for x in s["recall"].tolist()],
        }

    return {"g1_desp": g1_desp, "g1_banco": g1_banco, "g2_banco": g2_banco, "g2_desp": g2_desp, "g3": g3, "g4": g4}


if __name__ == "__main__":
    datos = recopilar_datos()
    out_json = OUT_DIR / "datos_graficas.json"
    out_json.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf8")
    print("Datos recopilados correctamente en:", out_json)
