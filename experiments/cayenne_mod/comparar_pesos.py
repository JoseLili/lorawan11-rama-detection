"""Experimento local exhaustivo; no entrena detectores ni simula LoRaWAN.

Cada escenario altera un único mensaje. Las frecuencias de valores conservan
exactamente los conteos de cruces locales, pero no describen eventos de red.
"""

from __future__ import annotations

from itertools import combinations
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import platform

import numpy as np
import pandas as pd


FORMATOS = ("actual", "binario_8_control", "v1", "v2")
# Los grupos indican dónde se reparte cada contribución binaria original.
GRUPOS = {
    "v1": ((0,), (1,), (2,), (3,), (4,), (5, 8), (6,), (7,)),
    "v2": ((0,), (1,), (2,), (3,), (4,), (5, 8), (6, 9), (7, 10, 11, 12)),
}
PESOS = {
    "v1": (1, 2, 4, 8, 16, 16, 64, 128, 16),
    "v2": (1, 2, 4, 8, 16, 16, 32, 32, 16, 32, 32, 32, 32),
}


def codificar(valor: int, formato: str) -> int:
    """Devuelve la palabra de 16 bits; todos admiten originales 0..255."""
    if formato not in FORMATOS:
        raise ValueError("Formato desconocido")
    if not isinstance(valor, (int, np.integer)) or not 0 <= valor <= 255:
        raise ValueError("El dominio experimental es entero, 0..255 ppb")
    if formato in ("actual", "binario_8_control"):
        return int(valor)
    return sum(1 << posicion
               for bit, grupo in enumerate(GRUPOS[formato])
               if (int(valor) >> bit) & 1
               for posicion in grupo)


def decodificar(palabra: int, formato: str) -> int | None:
    """None = rechazo de formato; nunca se sustituye un rechazo por cero.

    'actual' conserva la interpretación con signo del repositorio, incluso
    negativos. El control añade al binario el mismo dominio 0..255 y rechaza
    posiciones superiores. V1/V2 rechazan posiciones reservadas; admiten
    fragmentos discordantes y suman sus pesos, como la V1 del notebook 02.
    """
    if formato not in FORMATOS:
        raise ValueError("Formato desconocido")
    if not isinstance(palabra, (int, np.integer)) or not 0 <= palabra < 65536:
        raise ValueError("Se requiere una palabra de 16 bits")
    palabra = int(palabra)
    if formato == "actual":
        return palabra if palabra < 32768 else palabra - 65536
    if formato == "binario_8_control":
        return palabra if palabra < 256 else None
    pesos = PESOS[formato]
    if palabra >> len(pesos):
        return None
    return sum(peso for bit, peso in enumerate(pesos) if (palabra >> bit) & 1)


def mascaras(n_flips: int) -> tuple[list[str], np.ndarray]:
    if n_flips not in (1, 2):
        raise ValueError("Este experimento separa presupuestos de 1 y 2 flips")
    grupos = list(combinations(range(16), n_flips))
    return (["+".join(map(str, bits)) for bits in grupos],
            np.array([sum(1 << bit for bit in bits) for bits in grupos]))


@lru_cache(maxsize=32)
def tabla_transiciones(formato: str, n_flips: int, umbral: int = 155):
    """Enumera los 256 valores y TODAS las máscaras físicas del presupuesto."""
    etiquetas, masks = mascaras(n_flips)
    originales = np.arange(256)
    palabras = np.array([codificar(int(v), formato) for v in originales])
    recibidos = np.array([
        [np.nan if (d := decodificar(int(w ^ m), formato)) is None else d
         for m in masks] for w in palabras
    ])
    aceptados = np.isfinite(recibidos)
    sube = aceptados & (originales[:, None] < umbral) & (recibidos >= umbral)
    baja = aceptados & (originales[:, None] >= umbral) & (recibidos < umbral)
    delta = np.where(aceptados, np.abs(recibidos - originales[:, None]), 0)
    fuera = aceptados & ((recibidos < 0) | (recibidos > 255))
    return etiquetas, recibidos, {"cruces_arriba": sube, "cruces_abajo": baja,
                                "rechazos": ~aceptados, "fuera_0_255": fuera,
                                "suma_delta_aceptados": delta}


def evaluar(frecuencias: np.ndarray, formato: str, n_flips: int,
            umbral: int = 155) -> tuple[dict, pd.DataFrame]:
    """Pondera exactamente los escenarios; no muestrea ni usa semillas."""
    frecuencias = np.asarray(frecuencias)
    if (frecuencias.shape != (256,) or not np.isfinite(frecuencias).all()
            or (frecuencias < 0).any() or (frecuencias != frecuencias.astype(int)).any()
            or frecuencias.sum() == 0):
        raise ValueError("Se requieren 256 frecuencias enteras no negativas y datos")
    if not isinstance(umbral, int) or not 1 <= umbral <= 255:
        raise ValueError("Umbral fuera del dominio experimental")
    etiquetas, recibidos, eventos = tabla_transiciones(formato, n_flips, umbral)
    por_mascara = pd.DataFrame({"formato": formato, "n_flips": n_flips,
                                "bits": etiquetas})
    for nombre, matriz in eventos.items():
        por_mascara[nombre] = frecuencias @ matriz.astype(np.int64)
    n = int(frecuencias.sum())
    n_bajo = int(frecuencias[:umbral].sum())
    n_alto = n - n_bajo
    m = len(etiquetas)
    por_mascara["n_mensajes"] = n
    por_mascara["cruces"] = por_mascara.cruces_arriba + por_mascara.cruces_abajo
    por_mascara["pct_cruces"] = 100 * por_mascara.cruces / n
    por_mascara["pct_rechazos"] = 100 * por_mascara.rechazos / n
    total = n * m
    conteos = {k: int(por_mascara[k].sum()) for k in eventos}
    cruces = conteos["cruces_arriba"] + conteos["cruces_abajo"]
    aceptados = total - conteos["rechazos"]
    deltas = np.abs(recibidos[frecuencias > 0] - np.arange(256)[frecuencias > 0, None])
    peor = por_mascara.loc[por_mascara.cruces.idxmax()]
    resumen = {
        "formato": formato, "n_flips": n_flips, "n_mensajes": n,
        "n_bajo_umbral": n_bajo, "n_sobre_umbral": n_alto,
        "n_mascaras": m, "n_escenarios": total, **conteos, "cruces": cruces,
        "pct_cruces_uniforme": 100 * cruces / total,
        "pct_arriba_dado_bajo": 100 * conteos["cruces_arriba"] / (n_bajo*m) if n_bajo else np.nan,
        "pct_abajo_dado_alto": 100 * conteos["cruces_abajo"] / (n_alto*m) if n_alto else np.nan,
        "pct_rechazos": 100 * conteos["rechazos"] / total,
        "pct_cruce_o_rechazo": 100 * (cruces + conteos["rechazos"]) / total,
        "delta_medio_aceptados": conteos["suma_delta_aceptados"] / aceptados if aceptados else np.nan,
        "delta_max_aceptados": float(np.nanmax(deltas)),
        "peor_mascara_fija": peor.bits,
        "pct_cruces_peor_mascara_fija": peor.pct_cruces,
    }
    return resumen, por_mascara


def ejecutar(raiz: Path, destino: Path, umbral: int = 155):
    from src.ingest.rama import load_wide, to_long

    archivo = raiz / "data/raw/2025O3.xls"
    datos = to_long(load_wide(archivo), "O3")
    if datos.duplicated(["station", "timestamp"]).any():
        raise ValueError("Registros estación–hora duplicados")
    if not datos.timestamp.dt.year.eq(2025).all():
        raise ValueError("Se esperaban exclusivamente fechas de 2025")
    datos = datos.dropna(subset=["value"]).copy()
    valores = datos.value.to_numpy()
    if (not np.isfinite(valores).all() or (valores != np.rint(valores)).any()
            or (valores < 0).any() or (valores > 255).any()):
        raise ValueError("Hay datos fuera del dominio 0..255; no se recortan ni omiten")
    datos["ppb"] = valores.astype(int)
    grupos = [("TODAS", datos)] + list(datos.groupby("station", sort=True))
    resumenes, detalles, frecuencias = [], [], []
    for estacion, grupo in grupos:
        hist = np.bincount(grupo.ppb, minlength=256)
        frecuencias.append(pd.DataFrame({"station": estacion, "ppb": np.arange(256), "n": hist}))
        for formato in FORMATOS:
            for n_flips in (1, 2):
                resumen, detalle = evaluar(hist, formato, n_flips, umbral)
                resumenes.append({"station": estacion, **resumen})
                if estacion == "TODAS":
                    detalles.append(detalle)
    resumen = pd.DataFrame(resumenes)
    detalle = pd.concat(detalles, ignore_index=True)
    destino.mkdir(parents=True, exist_ok=True)
    resumen.to_csv(destino / "resumen.csv", index=False)
    detalle.to_csv(destino / "por_mascara.csv", index=False)
    pd.concat(frecuencias, ignore_index=True).to_csv(destino / "frecuencias.csv", index=False)
    metadatos = {
        "dataset": str(archivo.relative_to(raiz)),
        "sha256_dataset": hashlib.sha256(archivo.read_bytes()).hexdigest(),
        "sha256_codigo": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
        "umbral_ppb": umbral, "condicion_alta": "valor >= umbral",
        "dominio_originales": [0, 255], "n_validos": len(datos),
        "n_estaciones": datos.station.nunique(), "n_sobre_umbral": int((datos.ppb >= umbral).sum()),
        "pesos": PESOS, "grupos": GRUPOS, "formatos": FORMATOS,
        "presupuestos": [1, 2], "posiciones_atacables": list(range(16)),
        "escenario": "un mensaje alterado; cruces locales, no eventos de red",
        "politicas": "uniforme sobre mascaras fisicas; peor mascara fija global",
        "control": "binario_8_control agrega rechazo fuera de 0..255 al formato actual",
        "rechazos": "separados; no son datos corregidos ni ausencia de daño",
        "alcance": "exploratorio 2025; sin cifrado, LSTM, interpolacion ni validacion externa",
    }
    (destino / "metadatos.json").write_text(json.dumps(metadatos, indent=2, ensure_ascii=False) + "\n")
    return resumen, detalle, metadatos


def graficar(resumen: pd.DataFrame, detalle: pd.DataFrame, destino: Path, umbral: int = 155):
    import matplotlib.pyplot as plt

    globales = resumen[resumen.station == "TODAS"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    columnas = [("pct_arriba_dado_bajo", f"Cruces arriba / escenarios originalmente <{umbral}"),
                ("pct_abajo_dado_alto", f"Cruces abajo / escenarios originalmente ≥{umbral}"),
                ("pct_rechazos", "Rechazos / todos los escenarios")]
    colores = ["#777777", "#4878a8", "#e69f00", "#009e73"]
    for fila, presupuesto in enumerate((1, 2)):
        df = globales[globales.n_flips == presupuesto].set_index("formato").loc[list(FORMATOS)]
        for ax, (columna, titulo) in zip(axes[fila], columnas):
            barras = ax.bar(["Actual", "Binario +\nrango", "V1", "V2"], df[columna], color=colores)
            ax.bar_label(barras, fmt="%.2f", padding=3, fontsize=9)
            ax.set(title=f"{presupuesto} flip(s) · {titulo}", ylabel="%", ylim=(0, max(1, df[columna].max()*1.25)))
            ax.grid(axis="y", alpha=.2)
    n = int(globales.iloc[0].n_mensajes)
    altos = int(globales.iloc[0].n_sobre_umbral)
    fig.suptitle("RAMA 2025 · Máscaras uniformes sobre las 16 posiciones del valor\n"
                 f"{n:,} lecturas; {altos} ≥{umbral} ppb · Cruces locales; rechazar pierde el mensaje", fontsize=12)
    fig.savefig(destino / "comparacion.png", dpi=170)

    fig_bits, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)
    for formato, color in zip(FORMATOS, colores):
        df = detalle[(detalle.formato == formato) & (detalle.n_flips == 1)]
        ax.plot(df.bits.astype(int), df.pct_cruces, marker="o", label=formato, color=color)
    ax.set(xticks=range(16), xlabel="Posición física invertida (siempre la misma en esta curva)",
           ylabel=f"% de lecturas que cruzan {umbral} ppb", title="Un flip · Riesgo por posición elegida por el atacante")
    ax.legend()
    ax.grid(alpha=.2)
    fig_bits.savefig(destino / "cruces_por_bit.png", dpi=170)
    return fig, fig_bits
