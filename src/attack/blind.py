"""Generacion de datasets atacados.

Atacante ciego situado entre Network Server y Application Server:
observa texto cifrado, no posee AppSKey, y por tanto NO conoce el estado
previo del bit que voltea. No controla la direccion del daño.

El ataque se genera SIEMPRE despues del split cronologico. Atacar antes
de partir permitiria que la misma lectura aparezca atacada en un conjunto
y limpia en el otro.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.decision.damage import clasificar, daño, severidad
from src.encoding.cayenne import decode_o3, encode_o3, flip_bit
from src.encoding.crypto import decrypt, encrypt

DEVADDR = 0x26011BDA
APPSKEY = bytes(range(16))      # clave fija: los experimentos deben ser reproducibles


def _atacar_uno(ppb: int, bit: int, fcnt: int) -> int:
    """Cadena completa: codificar, cifrar, voltear bit, descifrar, decodificar.

    Pasa por el cifrado real en lugar de simular el flip sobre el entero,
    para que el dataset dependa de la implementacion que se defiende en la
    tesis y no de un atajo.
    """
    trama = encode_o3(int(ppb))
    cifrada = encrypt(trama, APPSKEY, DEVADDR, fcnt)
    atacada = flip_bit(cifrada, bit)
    return decode_o3(decrypt(atacada, APPSKEY, DEVADDR, fcnt))


def generar_dataset(
    serie: pd.DataFrame,
    bit: int,
    tasa: float = 0.05,
    seed: int = 42,
) -> pd.DataFrame:
    """Construye un dataset con una fraccion `tasa` de mensajes atacados.

    `serie` debe tener columnas: timestamp, value, y opcionalmente
    segment_id. Las filas con value nulo se conservan tal cual (no se
    atacan): un mensaje que no existe no puede ser manipulado.

    Devuelve un DataFrame con:
        original_value   verdad de campo. NUNCA debe usarse como feature.
        received_value   lo que el AS observa. Unica entrada legitima.
        atacado          etiqueta binaria (verdad de campo)
        bit              bit atacado, o -1
        banda_real       f(original_value)
        banda_recibida   f(received_value)
        daño             1 si el ataque cambio la banda
        severidad        bandas saltadas, con signo
        efecto           inflado | ocultamiento | sin_efecto
        hora             hora del dia (feature legitima)
        delta_t          horas desde el mensaje anterior
    """
    if not 0.0 <= tasa <= 1.0:
        raise ValueError("tasa debe estar en [0, 1]")

    rng = np.random.default_rng(seed)
    df = serie.copy().reset_index(drop=True)

    validas = df["value"].notna()
    marcados = validas & (rng.random(len(df)) < tasa)

    df["original_value"] = df["value"]
    df["received_value"] = df["value"]
    df["atacado"] = marcados.astype(int)
    df["bit"] = np.where(marcados, bit, -1)

    # FCnt incremental: cada mensaje usa un keystream distinto
    for i in df.index[marcados]:
        df.loc[i, "received_value"] = _atacar_uno(df.loc[i, "value"], bit, i + 1)

    # Metricas de daño, solo donde hay valor
    m = df["received_value"].notna() & df["original_value"].notna()
    for col in ("banda_real", "banda_recibida", "daño", "severidad"):
        df[col] = np.nan
    df["efecto"] = None

    if m.any():
        real = df.loc[m, "original_value"]
        recv = df.loc[m, "received_value"]
        # banda_o3 rechaza negativos: el bit 15 produce lecturas imposibles
        neg = recv < 0
        ok = m & ~neg.reindex(df.index, fill_value=False)

        from src.decision.nom172 import banda_o3
        df.loc[ok, "banda_real"] = banda_o3(df.loc[ok, "original_value"])
        df.loc[ok, "banda_recibida"] = banda_o3(df.loc[ok, "received_value"])
        df.loc[ok, "daño"] = daño(df.loc[ok, "original_value"],
                                  df.loc[ok, "received_value"])
        df.loc[ok, "severidad"] = severidad(df.loc[ok, "original_value"],
                                            df.loc[ok, "received_value"])
        df.loc[ok, "efecto"] = clasificar(df.loc[ok, "original_value"].values,
                                          df.loc[ok, "received_value"].values)

    # Features temporales
    df["hora"] = df["timestamp"].dt.hour
    if "segment_id" in df.columns:
        df["delta_t"] = (
            df.groupby("segment_id")["timestamp"].diff().dt.total_seconds() / 3600
        )
    else:
        df["delta_t"] = df["timestamp"].diff().dt.total_seconds() / 3600

    return df.drop(columns=["value"])

def guardar_csv(df: pd.DataFrame, ruta: str) -> None:
    """Exporta el dataset con las columnas ordenadas para revision manual.

    Incluye original_value, que es VERDAD DE CAMPO y no debe usarse como
    caracteristica del modelo. Se exporta solo para inspeccion.
    """
    cols = [
        "timestamp", "hora", "delta_t",
        "original_value", "received_value", "atacado", "bit",
        "banda_real", "banda_recibida", "daño", "severidad", "efecto",
    ]
    cols = [c for c in cols if c in df.columns]
    df[cols].to_csv(ruta, index=False)
