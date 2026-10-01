"""Experimento 05: dos distribuciones propuestas, un flip y detectores fijos.

Reutiliza predicciones verificadas del notebook 09. No importa TensorFlow ni
entrena. Todas las posiciones del campo de 16 bits reciben el mismo barrido.
"""
from pathlib import Path
import hashlib
import json
import platform

import numpy as np
import pandas as pd

from experiments.graficas_revision.generar import verificar_fuentes
from src.detect.red import contexto_diario, efectos_red
from src.ingest.rama import load_wide, to_long

FORMATOS = ("base", "A", "B")
PESOS = {
    "base": (1, 2, 4, 8, 16, 32, 64, 128),
    "A": (1, 2, 4, 8, 8, 16, 64, 128, 8, 16),
    "B": (1, 2, 4, 8, 8, 8, 64, 128, 8, 8, 8, 8),
}
GRUPOS = {
    "base": ((0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,)),
    "A": ((0,), (1,), (2,), (3,), (4, 8), (5, 9), (6,), (7,)),
    "B": ((0,), (1,), (2,), (3,), (4, 8), (5, 9, 10, 11), (6,), (7,)),
}
TIPOS = ("cambio_banda_red", "falsa_fase1", "anulada_fase1")


def codificar(valor, formato):
    if formato not in FORMATOS:
        raise ValueError("Formato desconocido")
    if not isinstance(valor, (int, np.integer)) or not 0 <= valor <= 255:
        raise ValueError("El dominio experimental es entero, 0..255 ppb")
    palabra = sum(1 << posicion for bit, grupo in enumerate(GRUPOS[formato])
                  if (int(valor) >> bit) & 1 for posicion in grupo)
    return bytes([1, 2]) + palabra.to_bytes(2, "big")


def decodificar(payload, formato):
    """None indica rechazo. Fragmentos discordantes se suman, no se corrigen."""
    if formato not in FORMATOS:
        raise ValueError("Formato desconocido")
    if len(payload) != 4 or payload[:2] != bytes([1, 2]):
        raise ValueError("Se requieren canal 1, tipo experimental 02 y cuatro bytes")
    palabra = int.from_bytes(payload[2:], "big")
    if palabra >> len(PESOS[formato]):
        return None
    return sum(peso for bit, peso in enumerate(PESOS[formato]) if (palabra >> bit) & 1)


def tabla_recibidos(formato):
    from src.encoding.cayenne import flip_bit
    tabla = np.full((256, 16), np.nan)
    for valor in range(256):
        payload = codificar(valor, formato)
        assert decodificar(payload, formato) == valor
        for bit in range(16):
            recibido = decodificar(flip_bit(payload, bit), formato)
            if recibido is not None:
                tabla[valor, bit] = recibido
    return tabla


def validar_cifrado():
    """Comprueba toda la tabla contra cifrar/flip/descifrar del repositorio.

    Valida la transformación del FRMPayload bajo el modelo de amenaza de la
    tesis; no simula radios, MIC, retransmisiones ni decisiones administrativas.
    """
    from src.encoding.cayenne import flip_bit
    from src.encoding.crypto import encrypt, decrypt
    from src.attack.blind import APPSKEY, DEVADDR
    n = 0
    for formato in FORMATOS:
        esperada = tabla_recibidos(formato)
        for valor in range(256):
            payload = codificar(valor, formato)
            cifrada = encrypt(payload, APPSKEY, DEVADDR, valor + 1)
            for bit in range(16):
                recuperada = decrypt(flip_bit(cifrada, bit), APPSKEY, DEVADDR, valor + 1)
                assert recuperada == flip_bit(payload, bit)
                resultado = decodificar(recuperada, formato)
                assert ((resultado is None and np.isnan(esperada[valor, bit]))
                        or resultado == esperada[valor, bit])
                n += 1
    return n


def validar_originales(contexto):
    x = contexto.original_ppb.to_numpy()
    if (not np.isfinite(x).all() or (x != np.rint(x)).any()
            or (x < 0).any() or (x > 255).any()):
        raise ValueError("Originales fuera de 0..255; no se recortan ni descartan")
    return x.astype(int)


def evaluar_posicion(contexto, tabla, bit, con_lstm):
    """Un escenario por fila, sustituyendo exclusivamente el mensaje actual."""
    original = validar_originales(contexto)
    recibido = tabla[original, bit]
    aceptado = np.isfinite(recibido)
    # Marcador de cálculo para el rechazo: conserva original, pero NO se usa
    # para atribuir seguridad. Se excluye explícitamente de daño y detección.
    para_calculo = np.where(aceptado, recibido, original)
    efectos = efectos_red(contexto, para_calculo)
    salida = pd.DataFrame({"recibido_ppb": recibido, "aceptado": aceptado}, index=contexto.index)
    for tipo in TIPOS:
        salida[tipo] = aceptado & efectos[tipo].to_numpy()
    if con_lstm:
        if not contexto.evaluable.all():
            raise ValueError("No se atribuye detección a un mensaje sin modelo")
        # Misma aritmética float32 que la referencia del notebook 09.
        valor_modelo = (contexto.base_ppb.to_numpy(dtype=np.float32)
                        + (para_calculo-contexto.perfil_ppb.to_numpy()).astype(np.float32))
        residuo = np.abs(valor_modelo-contexto.predicho_ppb.to_numpy())
        salida["residuo_ppb"] = np.where(aceptado, residuo, np.nan)
        salida["detectado"] = aceptado & (residuo > contexto.umbral_ppb.to_numpy())
    return salida


def resumir(contexto, con_lstm):
    n = len(contexto)
    fechas = contexto.fecha.to_numpy()
    n_dias = contexto.fecha.nunique()
    filas, globales, pares, eventos, diarios = [], [], [], [], []
    referencia = [evaluar_posicion(contexto, tabla_recibidos("base"), b, con_lstm) for b in range(16)]
    for formato in FORMATOS:
        tabla = tabla_recibidos(formato)
        union_dano = {t: np.zeros(n, bool) for t in TIPOS}
        union_escape = {t: np.zeros(n, bool) for t in TIPOS}
        for bit in range(16):
            e = referencia[bit] if formato == "base" else evaluar_posicion(contexto, tabla, bit, con_lstm)
            r = referencia[bit]
            for tipo in TIPOS:
                dano = e[tipo].to_numpy()
                union_dano[tipo] |= dano
                row = dict(formato=formato, bit=bit, peso=PESOS[formato][bit] if bit < len(PESOS[formato]) else 0,
                           tipo_dano=tipo, n_mensajes=n, n_dias=n_dias,
                           rechazos=int((~e.aceptado).sum()), daninos=int(dano.sum()),
                           dias_vulnerables=int(len(np.unique(fechas[dano]))))
                d = pd.DataFrame({"fecha": fechas, "dano": dano})
                if con_lstm:
                    escape = dano & ~e.detectado.to_numpy()
                    previo = r[tipo].to_numpy() & ~r.detectado.to_numpy()
                    union_escape[tipo] |= escape
                    row.update(daninos_no_detectados=int(escape.sum()),
                               dias_dano_no_detectado=int(len(np.unique(fechas[escape]))),
                               alertas_aceptados=int(e.detectado.sum()))
                    d["escape"] = escape
                    pares.append(dict(formato=formato, bit=bit, tipo_dano=tipo,
                        escapan_base=int(previo.sum()), escapan_candidata=int(escape.sum()),
                        persisten=int((previo & escape).sum()),
                        eliminados=int((previo & ~escape).sum()), nuevos=int((~previo & escape).sum())))
                filas.append(row)
                d = d.groupby("fecha", sort=True).any().reset_index()
                d["formato"], d["bit"], d["tipo_dano"] = formato, bit, tipo
                diarios.append(d)
            if con_lstm:
                # Auditoría de todos los escenarios dañinos, detectados o no.
                daninos = e[list(TIPOS)].any(axis=1)
                detalle = contexto.loc[daninos, ["fecha", "timestamp", "estacion", "original_ppb",
                          "maximo_original_ppb", "maximo_otros_ppb", "predicho_ppb", "umbral_ppb"]].copy()
                for col in e.columns:
                    detalle[col] = e.loc[daninos, col]
                detalle["formato"], detalle["bit"] = formato, bit
                eventos.append(detalle)
        for tipo in TIPOS:
            bloque = pd.DataFrame([f for f in filas if f["formato"] == formato and f["tipo_dano"] == tipo])
            row = dict(formato=formato, tipo_dano=tipo, n_mensajes=n, n_dias=n_dias,
                       n_escenarios=16*n, rechazos=int(bloque.rechazos.sum()),
                       pct_rechazos=100*int(bloque.rechazos.sum())/(16*n),
                       daninos=int(bloque.daninos.sum()), pct_daninos_uniforme=100*int(bloque.daninos.sum())/(16*n),
                       dias_vulnerables_union=int(len(np.unique(fechas[union_dano[tipo]]))))
            if con_lstm:
                suma = int(bloque.daninos_no_detectados.sum())
                peor = bloque.loc[bloque.daninos_no_detectados.idxmax()]
                row.update(daninos_no_detectados=suma, pct_escape_uniforme=100*suma/(16*n),
                    dias_escape_union=int(len(np.unique(fechas[union_escape[tipo]]))),
                    peor_bit_fijo=int(peor.bit) if peor.daninos_no_detectados else np.nan,
                    escapes_peor_bit_fijo=int(peor.daninos_no_detectados),
                    pct_escape_peor_bit_fijo=100*int(peor.daninos_no_detectados)/n)
            globales.append(row)
    return {
        "resumen": pd.DataFrame(globales), "por_bit": pd.DataFrame(filas),
        "pareados": pd.DataFrame(pares), "por_dia": pd.concat(diarios, ignore_index=True),
        "eventos_daninos": pd.concat(eventos, ignore_index=True) if con_lstm else pd.DataFrame(),
    }


def construir(raiz):
    raiz = Path(raiz)
    carpeta, contexto, fuentes = verificar_fuentes(raiz)
    anteriores = pd.read_csv(carpeta / "eventos_aislados.csv.gz")
    tabla_base = tabla_recibidos("base")
    for bit, bloque in anteriores.groupby("bit", sort=True):
        assert bloque[["timestamp", "estacion"]].reset_index(drop=True).equals(contexto[["timestamp", "estacion"]])
        nuevo = evaluar_posicion(contexto, tabla_base, int(bit), True)
        for col in ["recibido_ppb", "detectado", *TIPOS]:
            np.testing.assert_array_equal(nuevo[col], bloque[col])
    for formato in FORMATOS:
        assert all(decodificar(codificar(x, formato), formato) == x for x in range(256))
    # Las mismas lecturas limpias => mismas alertas; no se recalibra p95.
    limpio = (contexto.base_ppb.to_numpy(dtype=np.float32)
              + (contexto.original_ppb.to_numpy()-contexto.perfil_ppb.to_numpy()).astype(np.float32))
    np.testing.assert_array_equal(np.abs(limpio-contexto.predicho_ppb.to_numpy()) > contexto.umbral_ppb.to_numpy(), contexto.alerta_limpia)
    test = resumir(contexto, True)
    matriz = (to_long(load_wide(raiz / "data/raw/2025O3.xls"), "O3")
              .pivot(index="timestamp", columns="station", values="value").sort_index().dropna(axis=1, how="all"))
    anual_contexto = contexto_diario(matriz)
    anual = resumir(anual_contexto, False)
    # En las posiciones 0..7, el caso base anual reproduce la revisión del 09.
    guardado = pd.read_csv(raiz / "results/revision_graficas_bits_0_7/efectos_anuales_sin_lstm.csv")
    for r in guardado.itertuples():
        for tipo, atributo in [("falsa_fase1", "dias_falsas_activaciones"), ("anulada_fase1", "dias_contingencias_ocultadas")]:
            g = anual["por_bit"].query("formato == 'base' and bit == @r.bit and tipo_dano == @tipo").iloc[0]
            assert g.dias_vulnerables == getattr(r, atributo)
    fuentes["results/revision_graficas_bits_0_7/efectos_anuales_sin_lstm.csv"] = hashlib.sha256((raiz / "results/revision_graficas_bits_0_7/efectos_anuales_sin_lstm.csv").read_bytes()).hexdigest()
    info = dict(fuentes=fuentes, pesos=PESOS, grupos=GRUPOS, dominio=[0, 255],
        bytes_payload=4, presupuesto_flips=1, posiciones=list(range(16)),
        test_mensajes=len(contexto), test_dias=contexto.fecha.nunique(),
        test_inicio=str(contexto.fecha.min().date()), test_fin=str(contexto.fecha.max().date()),
        test_maximo_ppb=float(contexto.maximo_original_ppb.max()),
        fpr_limpio_pct=100*float(contexto.alerta_limpia.mean()),
        anual_mensajes=len(anual_contexto), anual_dias=anual_contexto.fecha.nunique(),
        anual_dias_excedencia=int(anual_contexto.groupby("fecha").maximo_original_ppb.first().ge(155).sum()),
        modelo="Predicciones de modelos guardados y p95 por estación; sin inferencia nueva ni entrenamiento",
        ataque="Un mensaje actual por escenario; no se propaga a entradas de vecinos ni a perfiles futuros",
        base="Binario original en bits 0..7 + rechazo de posiciones 8..15 (control de dominio)",
        rechazos="Pérdida de lectura, no corrección; se excluyen de cruce y no se evalúa respuesta a su ausencia",
        politicas="Uniforme sobre 16 bits; peor bit fijo retrospectivo; unión de días con alguna oportunidad",
        python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__)
    return test, anual, info


def guardar(raiz, test, anual, info):
    destino = Path(raiz) / "experiments/cayenne_mod/resultados/05"
    codigo = [Path(__file__), Path(raiz)/"experiments/graficas_revision/generar.py",
              Path(raiz)/"src/encoding/cayenne.py", Path(raiz)/"src/encoding/crypto.py",
              Path(raiz)/"src/ingest/rama.py", Path(raiz)/"src/decision/nom172.py"]
    meta = dict(info, codigo_sha256={str(p.relative_to(raiz)): hashlib.sha256(p.read_bytes()).hexdigest() for p in codigo})
    protocolo = destino / "protocolo.json"
    normal = json.loads(json.dumps(meta))
    if protocolo.exists() and json.loads(protocolo.read_text()) != normal:
        raise ValueError("Cambió el protocolo o sus fuentes: use otro destino antes de sobrescribir resultados")
    destino.mkdir(parents=True, exist_ok=True)
    for prefijo, resultados in [("test", test), ("anual", anual)]:
        for nombre, df in resultados.items():
            if not df.empty:
                extension = ".csv.gz" if nombre in ("eventos_daninos", "por_dia") else ".csv"
                df.to_csv(destino / f"{prefijo}_{nombre}{extension}", index=False,
                          compression={"method": "gzip", "mtime": 0} if extension.endswith("gz") else None)
    protocolo.write_text(json.dumps(normal, indent=2, ensure_ascii=False)+"\n")
    return destino


def graficar(test, anual, destino):
    import matplotlib.pyplot as plt
    colores = {"base": "#555555", "A": "#d55e00", "B": "#0072b2"}
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    t = test["por_bit"].query("tipo_dano == 'cambio_banda_red'")
    for formato in FORMATOS:
        g = t[t.formato.eq(formato)]
        axes[0].plot(g.bit, g.daninos_no_detectados, "o-", label=formato, color=colores[formato])
        axes[1].plot(g.bit, g.dias_dano_no_detectado, "o-", label=formato, color=colores[formato])
    for ax in axes:
        ax.set(xlabel="Posición física del bit atacado", xticks=range(16))
        ax.grid(alpha=.2)
        ax.legend()
    axes[0].set(ylabel="Escenarios dañinos no detectados", title="Cambio de banda del máximo diario")
    axes[1].set(ylabel="Días con alguna oportunidad no detectada", title="Un día se cuenta una vez por bit")
    fig.suptitle("Un flip por mensaje · Detectores guardados del notebook 09, p95 por estación")
    fig.savefig(destino / "cambio_banda_por_bit.png", dpi=170)

    fig2, axes = plt.subplots(1, 3, figsize=(13, 5), constrained_layout=True)
    for ax, (col, titulo) in zip(axes, [("daninos_no_detectados", "Escenarios que escapan"),
                              ("dias_escape_union", "Días con alguna oportunidad (unión)"),
                              ("pct_rechazos", "Rechazos sobre todos los escenarios (%)")]):
        g = test["resumen"].query("tipo_dano == 'cambio_banda_red'").set_index("formato").loc[list(FORMATOS)]
        bars = ax.bar(g.index, g[col], color=[colores[f] for f in g.index])
        ax.bar_label(bars, fmt="%g", padding=3)
        ax.set(title=titulo, ylim=(0, max(g[col])*1.2))
        ax.grid(axis="y", alpha=.2)
    n = int(g.iloc[0].n_escenarios)
    fig2.suptitle(f"Mismo presupuesto: {n:,} escenarios por formato (mensajes × 16 bits)\n"
                  "Cambios de banda; los rechazos son pérdidas de datos, no lecturas corregidas")
    fig2.savefig(destino / "comparacion_formatos.png", dpi=170)

    fig3, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for ax, tipo, titulo in zip(axes, ["falsa_fase1", "anulada_fase1"], ["Falsas excedencias", "Ocultamientos de excedencias"]):
        g = anual["por_bit"].query("tipo_dano == @tipo")
        for formato in FORMATOS:
            f = g[g.formato.eq(formato)]
            ax.plot(f.bit, f.dias_vulnerables, "o-", label=formato, color=colores[formato])
        ax.set(title=titulo, xlabel="Posición física del bit", ylabel="Días con alguna oportunidad", xticks=range(16))
        ax.legend()
        ax.grid(alpha=.2)
    fig3.suptitle("Año completo, umbral ≥155 ppb · Un mensaje alterado por escenario · SIN LSTM")
    fig3.savefig(destino / "efectos_anuales.png", dpi=170)
    return fig, fig2, fig3
