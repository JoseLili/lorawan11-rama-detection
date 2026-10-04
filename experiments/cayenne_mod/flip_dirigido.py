"""Experimento 06: UN bit por mensaje, elegido dentro del grupo propuesto.

La enumeración de opciones calcula la esperanza del sorteo. No suma intentos
extra para A/B ni combina varios flips en una misma lectura.
"""
from pathlib import Path
import hashlib
import json
import platform

import numpy as np
import pandas as pd

from experiments.cayenne_mod.selectiva_red import (
    PESOS, GRUPOS, codificar, decodificar, tabla_recibidos, evaluar_posicion,
)
from experiments.graficas_revision.generar import verificar_fuentes
from src.detect.red import contexto_diario
from src.ingest.rama import load_wide, to_long

POOLS = {"base": (5,), "A": (5, 9), "B": (4, 8, 5, 9, 10, 11)}
TIPOS = ("cambio_banda_red", "falsa_fase1", "anulada_fase1")
SEMILLA = 42


def indices_sorteados(n, pool, u):
    u = np.asarray(u)
    if u.shape != (n,) or not np.isfinite(u).all() or (u < 0).any() or (u >= 1).any():
        raise ValueError("Se requieren n uniformes en [0, 1)")
    return np.floor(u * len(pool)).astype(int)


def evaluar(contexto, con_lstm, seed=SEMILLA):
    """El sorteo usa un uniforme común por mensaje para emparejar formatos.

    Cada fila siempre representa una alteración aislada; el sorteo sobre todos
    los mensajes no genera un día con todos sus mensajes atacados a la vez.
    """
    contexto = contexto.reset_index(drop=True)
    n = len(contexto)
    u = np.random.default_rng(seed).random(n)
    fechas = contexto.fecha
    sorteos, opciones, resumenes, probabilidades = [], [], [], []
    for formato, pool in POOLS.items():
        tabla = tabla_recibidos(formato)
        opciones_e = [evaluar_posicion(contexto, tabla, b, con_lstm) for b in pool]
        assert all(e.aceptado.all() for e in opciones_e), "Los grupos sólo contienen posiciones activas"
        matriz = np.column_stack([e.recibido_ppb for e in opciones_e])
        idx = indices_sorteados(n, pool, u)
        m = np.arange(n)
        fila = contexto[["fecha", "timestamp", "estacion", "original_ppb",
                         "maximo_original_ppb", "maximo_otros_ppb"]].copy()
        fila["formato"] = formato
        fila["bit_elegido"] = np.asarray(pool)[idx]
        fila["peso_elegido"] = [PESOS[formato][b] for b in fila.bit_elegido]
        fila["recibido_ppb"] = matriz[m, idx]
        fila["delta_ppb"] = fila.recibido_ppb - fila.original_ppb
        if con_lstm:
            fila["predicho_ppb"] = contexto.predicho_ppb
            fila["umbral_ppb"] = contexto.umbral_ppb
            for col in ("detectado", "residuo_ppb"):
                fila[col] = np.column_stack([e[col] for e in opciones_e])[m, idx]
        for tipo in TIPOS:
            dano = np.column_stack([e[tipo] for e in opciones_e])
            fila[tipo] = dano[m, idx]
            pr = dano.mean(axis=1)
            detalle = pd.DataFrame({"fecha": fechas, "formato": formato, "tipo_dano": tipo,
                                    "prob_dano": pr})
            r = dict(formato=formato, tipo_dano=tipo, mensajes=n,
                     opciones_por_mensaje=len(pool), peso_flip=int(PESOS[formato][pool[0]]),
                     dias_periodo=int(fechas.nunique()),
                     daninos_sorteo=int(fila[tipo].sum()),
                     daninos_esperados=float(pr.sum()), pct_dano_esperado=100*float(pr.mean()),
                     dias_dano_sorteo=int(fechas[fila[tipo]].nunique()),
                     dias_con_alguna_opcion_danina=int(fechas[pr > 0].nunique()))
            if con_lstm:
                alertas = np.column_stack([e.detectado for e in opciones_e])
                escapan = dano & ~alertas
                pe = escapan.mean(axis=1)
                fila[tipo+"_no_detectado"] = escapan[m, idx]
                detalle["prob_dano_no_detectado"] = pe
                r.update(escapan_sorteo=int(fila[tipo+"_no_detectado"].sum()),
                         escapan_esperados=float(pe.sum()), pct_escape_esperado=100*float(pe.mean()),
                         dias_escape_sorteo=int(fechas[fila[tipo+"_no_detectado"]].nunique()),
                         dias_con_alguna_opcion_escape=int(fechas[pe > 0].nunique()),
                         recall_global_esperado_pct=100*float(alertas.mean()),
                         recall_dano_esperado_pct=100*float((dano & alertas).sum()/dano.sum()) if dano.any() else np.nan)
            resumenes.append(r)
            probabilidades.append(detalle)
            for k, bit in enumerate(pool):
                op = dict(formato=formato, bit=bit, tipo_dano=tipo, mensajes=n,
                          peso=PESOS[formato][bit], prob_eleccion=1/len(pool),
                          daninos=int(dano[:, k].sum()))
                if con_lstm:
                    op["escapan"] = int(escapan[:, k].sum())
                opciones.append(op)
        sorteos.append(fila)
    return dict(resumen=pd.DataFrame(resumenes), por_opcion=pd.DataFrame(opciones),
                sorteo=pd.concat(sorteos, ignore_index=True),
                probabilidades=pd.concat(probabilidades, ignore_index=True))


def ejemplos():
    from src.encoding.cayenne import flip_bit
    filas = []
    for valor in (60, 28):
        for formato, pool in POOLS.items():
            payload = codificar(valor, formato)
            for bit in pool:
                recibido = decodificar(flip_bit(payload, bit), formato)
                filas.append(dict(original=valor, formato=formato, bit=bit, peso=PESOS[formato][bit],
                                  recibido=recibido, delta=recibido-valor,
                                  prob_eleccion=1/len(pool)))
    return pd.DataFrame(filas)


def construir(raiz):
    raiz = Path(raiz)
    carpeta, contexto, fuentes = verificar_fuentes(raiz)
    tabla = tabla_recibidos("base")
    base5 = evaluar_posicion(contexto, tabla, 5, True)
    anterior = pd.read_csv(carpeta / "eventos_aislados.csv.gz")
    anterior = anterior[anterior.bit.eq(5)].reset_index(drop=True)
    pd.testing.assert_frame_equal(anterior[["timestamp", "estacion"]], contexto[["timestamp", "estacion"]])
    for col in ("recibido_ppb", "detectado", *TIPOS):
        np.testing.assert_array_equal(base5[col], anterior[col])
    test = evaluar(contexto, True)
    matriz = (to_long(load_wide(raiz / "data/raw/2025O3.xls"), "O3")
              .pivot(index="timestamp", columns="station", values="value").sort_index().dropna(axis=1, how="all"))
    ctx_anual = contexto_diario(matriz)
    anual = evaluar(ctx_anual, False)
    info = dict(fuentes=fuentes, pools=POOLS, pesos=PESOS, grupos=GRUPOS,
        seed=SEMILLA, presupuesto_flips=1, dominio=[0,255],
        modelo="Predicciones y p95 por estación GUARDADOS del notebook 09; sin reentrenar ni recalibrar",
        periodo_test=[str(contexto.fecha.min().date()),str(contexto.fecha.max().date())],
        test_mensajes=len(contexto), test_dias=contexto.fecha.nunique(),
        test_maximo_ppb=float(contexto.maximo_original_ppb.max()),
        fpr_limpio_pct=100*float(contexto.alerta_limpia.mean()),
        anual_mensajes=len(ctx_anual), anual_dias=ctx_anual.fecha.nunique(),
        anual_dias_excedencia=int(ctx_anual.groupby("fecha").maximo_original_ppb.first().ge(155).sum()),
        muestreo="Uniforme común por mensaje; una posición por formato mediante floor(u * tamaño_grupo)",
        esperado="Promedio exacto de las opciones por mensaje: pesos 1, 1/2, 1/6; no suma de intentos",
        escenario="Un mensaje aislado en su contexto limpio por fila; no ataques simultáneos o persistentes",
        alcance_B="Incluye fragmentos de los bits originales 4 y 5; base/A sólo de 5; no aísla únicamente la contribución de 32",
        seleccion="Grupos fijados antes del ataque, sin consultar el estado del bit ni el valor",
        python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__)
    return test, anual, info


def guardar(raiz, test, anual, info):
    raiz = Path(raiz)
    destino = raiz / "experiments/cayenne_mod/resultados/06"
    archivos = [Path(__file__), raiz/"experiments/cayenne_mod/selectiva_red.py",
                raiz/"experiments/graficas_revision/generar.py", raiz/"src/decision/nom172.py",
                raiz/"src/encoding/cayenne.py", raiz/"src/encoding/crypto.py", raiz/"src/ingest/rama.py"]
    meta = dict(info, codigo_sha256={str(p.relative_to(raiz)): hashlib.sha256(p.read_bytes()).hexdigest() for p in archivos})
    meta = json.loads(json.dumps(meta))
    protocolo = destino/"protocolo.json"
    if protocolo.exists() and json.loads(protocolo.read_text()) != meta:
        raise ValueError("Fuentes o protocolo distintos: no se sobrescribe esta referencia")
    destino.mkdir(parents=True, exist_ok=True)
    for prefijo, resultados in [("test",test), ("anual",anual)]:
        for nombre, df in resultados.items():
            comprimido = nombre in ("sorteo","probabilidades")
            df.to_csv(destino/f"{prefijo}_{nombre}.csv{'.gz' if comprimido else ''}",index=False,
                      compression={"method":"gzip","mtime":0} if comprimido else None)
    ejemplos().to_csv(destino/"ejemplos_60_28.csv",index=False)
    protocolo.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+"\n")
    return destino


def graficar(test, destino):
    import matplotlib.pyplot as plt
    t = test["resumen"].query("tipo_dano == 'cambio_banda_red'").set_index("formato").loc[list(POOLS)]
    fig, axes = plt.subplots(1,2,figsize=(12,4.8),constrained_layout=True)
    colores = ["#555555","#d55e00","#0072b2"]
    for ax, col, titulo in zip(axes,["daninos_esperados","escapan_esperados"],
                              ["Cambian la banda del máximo diario", "Cambian la banda Y no generan alerta"]):
        bars = ax.bar(t.index,t[col],color=colores)
        ax.bar_label(bars,fmt="%.2f",padding=3)
        ax.set(title=titulo,ylabel="Número esperado de escenarios",ylim=(0,max(t[col])*1.25))
        ax.grid(axis="y",alpha=.2)
    fig.suptitle(f"Un flip dentro del grupo propuesto · Mismos {int(t.iloc[0].mensajes):,} mensajes\n"
                 "Promedio exacto de la selección aleatoria; predicciones y p95 guardados")
    fig.savefig(destino/"comparacion_dirigida.png",dpi=170)
    return fig
