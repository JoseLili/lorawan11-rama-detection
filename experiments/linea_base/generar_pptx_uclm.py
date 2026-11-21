"""Genera el archivo PowerPoint editable de 12 láminas (Presentacion_Coloquio_UCLM_JELB.pptx).

Conserva el tema, tipografías y estilos maestros de Parte3_detector_final.pptx,
inserta los 3 diagramas y las 4 gráficas en alta resolución, deja texto mínimo
en pantalla y guarda el guion detallado del orador en las notas de cada diapositiva.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
IMG_DIR = ROOT / "docs" / "img" / "coloquio_uclm"
TEMPLATE_PPTX = Path(
    r"C:\Users\jose_\.gemini\antigravity\brain\69484fbb-153d-4dc8-bbe3-c46870f09661\.user_uploaded\media_1794281490385_fdcfb7aa.pptx"
)
OUT_PPTX = ROOT / "docs" / "Presentacion_Coloquio_UCLM_JELB.pptx"
ART_PPTX = Path(
    r"C:\Users\jose_\.gemini\antigravity\brain\69484fbb-153d-4dc8-bbe3-c46870f09661\Presentacion_Coloquio_UCLM_JELB.pptx"
)


def xml_textbox(
    shape_id: int,
    x: int,
    y: int,
    cx: int,
    cy: int,
    paragraphs: list[tuple[str, int, str, bool, bool, str, str]],
) -> str:
    """Construye un <p:sp> de texto.

    Cada párrafo: (texto, tamaño_pt100, color_hex, bold, italic, font_name, align)
    """
    ps = []
    for txt, sz, col, bold, italic, font, algn in paragraphs:
        b_attr = ' b="1"' if bold else ' b="0"'
        i_attr = ' i="1"' if italic else ' i="0"'
        ps.append(
            f'<a:p><a:pPr algn="{algn}"/><a:r>'
            f'<a:rPr lang="es-MX" sz="{sz}"{b_attr}{i_attr} dirty="0">'
            f'<a:solidFill><a:srgbClr val="{col}"/></a:solidFill>'
            f'<a:latin typeface="{font}"/></a:rPr>'
            f'<a:t>{escape(txt)}</a:t></a:r></a:p>'
        )
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="TextBox {shape_id}"/>'
        f'<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
        f'<p:txBody><a:bodyPr wrap="square" lIns="36576" tIns="36576" rIns="36576" bIns="36576" anchor="t">'
        f'<a:spAutoFit/></a:bodyPr><a:lstStyle/>{"".join(ps)}</p:txBody></p:sp>'
    )


def xml_card(
    shape_id: int,
    x: int,
    y: int,
    cx: int,
    cy: int,
    bg_hex: str,
    bd_hex: str,
    paragraphs: list[tuple[str, int, str, bool, bool, str, str, int]],
) -> str:
    """Construye una tarjeta redondeada (<p:sp> roundRect).

    Cada párrafo: (texto, sz_pt100, color_hex, bold, italic, font, align, spc_before_pt100)
    """
    ps = []
    for txt, sz, col, bold, italic, font, algn, spc in paragraphs:
        b_attr = ' b="1"' if bold else ' b="0"'
        i_attr = ' i="1"' if italic else ' i="0"'
        spc_xml = f'<a:spcBef><a:spcPts val="{spc}"/></a:spcBef>' if spc > 0 else ""
        ps.append(
            f'<a:p><a:pPr algn="{algn}">{spc_xml}</a:pPr><a:r>'
            f'<a:rPr lang="es-MX" sz="{sz}"{b_attr}{i_attr} dirty="0">'
            f'<a:solidFill><a:srgbClr val="{col}"/></a:solidFill>'
            f'<a:latin typeface="{font}"/></a:rPr>'
            f'<a:t>{escape(txt)}</a:t></a:r></a:p>'
        )
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="Card {shape_id}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 4000"/></a:avLst></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{bg_hex}"/></a:solidFill>'
        f'<a:ln w="15875"><a:solidFill><a:srgbClr val="{bd_hex}"/></a:solidFill></a:ln><a:effectLst/></p:spPr>'
        f'<p:txBody><a:bodyPr wrap="square" lIns="182880" tIns="160000" rIns="182880" bIns="160000" anchor="t"/>'
        f'<a:lstStyle/>{"".join(ps)}</p:txBody></p:sp>'
    )


def xml_picture(shape_id: int, r_id: str, x: int, y: int, cx: int, cy: int) -> str:
    return (
        f'<p:pic><p:nvPicPr><p:cNvPr id="{shape_id}" name="Picture {shape_id}"/><p:cNvPicPr>'
        f'<a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
        f'<p:blipFill><a:blip r:embed="{r_id}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
    )


def xml_table(
    shape_id: int,
    x: int,
    y: int,
    cx: int,
    cy: int,
    col_widths: list[int],
    headers: list[str],
    rows: list[list[str]],
) -> str:
    grid_cols = "".join(f'<a:gridCol w="{w}"/>' for w in col_widths)
    row_h = int(cy / (len(rows) + 1))

    def make_cell(text: str, bg: str, fg: str, bold: bool, sz: int, align: str = "l") -> str:
        b_attr = ' b="1"' if bold else ' b="0"'
        return (
            f'<a:tc><a:txBody><a:bodyPr/><a:lstStyle/>'
            f'<a:p><a:pPr algn="{align}"/><a:r>'
            f'<a:rPr lang="es-MX" sz="{sz}"{b_attr} i="0" dirty="0">'
            f'<a:solidFill><a:srgbClr val="{fg}"/></a:solidFill>'
            f'<a:latin typeface="Segoe UI"/></a:rPr>'
            f'<a:t>{escape(text)}</a:t></a:r></a:p></a:txBody>'
            f'<a:tcPr marL="109728" marR="109728" marT="54864" marB="54864" anchor="ctr">'
            f'<a:solidFill><a:srgbClr val="{bg}"/></a:solidFill></a:tcPr></a:tc>'
        )

    hdr_cells = "".join(make_cell(h, "1B2A4A", "FFFFFF", True, 1500, "l") for h in headers)
    trs = [f'<a:tr h="{row_h}">{hdr_cells}</a:tr>']
    for r_idx, r in enumerate(rows):
        bg = "FFFFFF" if r_idx % 2 == 0 else "F4F0E8"
        cells = "".join(
            make_cell(c, bg, "1B2A4A" if c_idx == 0 else "243040", c_idx == 0, 1450, "l")
            for c_idx, c in enumerate(r)
        )
        trs.append(f'<a:tr h="{row_h}">{cells}</a:tr>')

    return (
        f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{shape_id}" name="Table {shape_id}"/>'
        f'<p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
        f'<p:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></p:xfrm>'
        f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
        f'<a:tbl><a:tblPr><a:tableStyleId>{{5940675A-B579-460E-94D1-54222C63F5DA}}</a:tableStyleId></a:tblPr>'
        f'<a:tblGrid>{grid_cols}</a:tblGrid>{"".join(trs)}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>'
    )


def wrap_slide(bg_hex: str, shapes: list[str], slide_num: int | None = None) -> str:
    num_xml = ""
    if slide_num is not None:
        num_col = "C9CED8" if bg_hex == "172540" else "6B6B6B"
        num_xml = xml_textbox(
            99,
            11155680,
            6400800,
            548640,
            274320,
            [(f"{slide_num} / 12", 1050, num_col, False, False, "Segoe UI", "r")],
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        f'<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{bg_hex}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
        '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        f'{"".join(shapes)}{num_xml}'
        '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
    )


def header_shapes(tag: str, title: str) -> list[str]:
    return [
        xml_textbox(2, 548640, 320000, 11064240, 300000, [(tag, 1150, "C8641E", True, False, "Segoe UI", "l")]),
        xml_textbox(3, 548640, 580000, 11064240, 520000, [(title, 2500, "1B2A4A", False, False, "Cambria", "l")]),
    ]


def fit_image_box(img_w: int, img_h: int, box_x: int, box_y: int, box_w: int, box_h: int) -> tuple[int, int, int, int]:
    """Centra la imagen preservando exactamente su proporción de aspecto."""
    scale = min(box_w / img_w, box_h / img_h)
    w = int(img_w * scale)
    h = int(img_h * scale)
    x = box_x + (box_w - w) // 2
    y = box_y + (box_h - h) // 2
    return x, y, w, h


def make_notes_xml(slide_num: int, notes_lines: list[str]) -> str:
    paras = "".join(
        f'<a:p><a:r><a:rPr lang="es-MX" sz="1200" dirty="0"/><a:t>{escape(line)}</a:t></a:r></a:p>'
        for line in notes_lines
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image Placeholder 1"/><p:cNvSpPr><a:spLocks noGrp="1" noRot="1" noChangeAspect="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldImg" idx="2"/></p:nvPr></p:nvSpPr><p:spPr/></p:sp>'
        f'<p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes Placeholder 2"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" sz="quarter" idx="3"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>{paras}</p:txBody></p:sp>'
        f'<p:sp><p:nvSpPr><p:cNvPr id="4" name="Slide Number Placeholder 3"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldNum" sz="quarter" idx="10"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:fld id="{{3B00D679-4E30-427C-9E32-699B1D5C1301}}" type="slidenum"><a:rPr lang="es-MX" smtClean="0"/><a:t>{slide_num}</a:t></a:fld><a:endParaRPr lang="es-MX"/></a:p></p:txBody></p:sp>'
        '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>'
    )


def construir_diapositivas() -> tuple[list[str], dict[int, tuple[str, Path]], list[list[str]]]:
    slides_xml: list[str] = []
    media_map: dict[int, tuple[str, Path]] = {}
    notes_list: list[list[str]] = []

    # -------------------------------------------------------------------------
    # LÁMINA 1: PORTADA
    # -------------------------------------------------------------------------
    s1 = wrap_slide(
        "172540",
        [
            xml_textbox(
                2, 731520, 1250000, 10700000, 360000,
                [("POSGRADO EN CIENCIA E INGENIERÍA DE LA COMPUTACIÓN · UNAM", 1250, "C8641E", True, False, "Segoe UI", "l")],
            ),
            xml_textbox(
                3, 731520, 1720000, 10700000, 1650000,
                [
                    ("Detección de anomalías de integridad en", 3600, "FFFFFF", False, False, "Cambria", "l"),
                    ("redes de monitoreo atmosférico", 3600, "FFFFFF", False, False, "Cambria", "l"),
                ],
            ),
            xml_textbox(
                4, 731520, 3550000, 10500000, 750000,
                [
                    ("Aprendizaje profundo con contraste espacio-temporal y exploración con imágenes sintéticas TINTO", 1800, "E8EBF1", False, False, "Segoe UI", "l"),
                ],
            ),
            xml_textbox(
                5, 731520, 5550000, 10500000, 650000,
                [
                    ("Presenta: Ing. José Emiliano Lili Beltrán", 1500, "FFFFFF", True, False, "Segoe UI", "l"),
                    ("Tutor: Dr. José Jaime Camacho Escoto   ·   Noviembre de 2026", 1350, "C9CED8", False, False, "Segoe UI", "l"),
                ],
            ),
        ],
        slide_num=1,
    )
    slides_xml.append(s1)
    notes_list.append([
        "LÁMINA 1 — PORTADA",
        "• Presentación de avances y resultados del detector final de anomalías sobre la Red Automática de Monitoreo Atmosférico (RAMA) de la Ciudad de México.",
        "• Incluye los resultados consolidados del Ensamble vecinal con filtro y los experimentos iniciales con la representación visual TINTO.",
    ])

    # -------------------------------------------------------------------------
    # LÁMINA 2: CONTEXTO Y PROBLEMA
    # -------------------------------------------------------------------------
    cw = 3480000
    gap = 310000
    x0 = 548640
    cy = 1550000
    ch = 4450000
    s2 = wrap_slide(
        "F4F0E8",
        header_shapes("CONTEXTO Y PROBLEMA", "Integridad de mediciones en redes con alta varianza natural")
        + [
            xml_card(
                4, x0, cy, cw, ch, "FFFFFF", "0F4C81",
                [
                    ("1. Red RAMA (CDMX)", 1900, "0F4C81", True, False, "Segoe UI", "l", 0),
                    ("32 estaciones · Ozono (O₃)", 1600, "1B2A4A", True, False, "Segoe UI", "l", 1800),
                    ("• Mediciones horarias.", 1500, "243040", False, False, "Segoe UI", "l", 1600),
                    ("• Alta varianza diurna, estacional y meteorológica.", 1500, "243040", False, False, "Segoe UI", "l", 1200),
                    ("• Oculta alteraciones sutiles.", 1500, "243040", False, False, "Segoe UI", "l", 1200),
                ],
            ),
            xml_card(
                5, x0 + cw + gap, cy, cw, ch, "FFFFFF", "D97724",
                [
                    ("2. Anomalías y amenazas", 1900, "D97724", True, False, "Segoe UI", "l", 0),
                    ("Datos falsos con formato válido", 1600, "1B2A4A", True, False, "Segoe UI", "l", 1800),
                    ("• Fallas o degradación física.", 1500, "243040", False, False, "Segoe UI", "l", 1600),
                    ("• Descalibración progresiva.", 1500, "243040", False, False, "Segoe UI", "l", 1200),
                    ("• Ataques de integridad en el enlace.", 1500, "243040", False, False, "Segoe UI", "l", 1200),
                ],
            ),
            xml_card(
                6, x0 + 2 * (cw + gap), cy, cw, ch, "FFFFFF", "1B9E77",
                [
                    ("3. Reto operativo", 1900, "1B9E77", True, False, "Segoe UI", "l", 0),
                    ("Sistema de alerta temprana", 1600, "1B2A4A", True, False, "Segoe UI", "l", 1800),
                    ("• Sin agregar nodos ni hardware.", 1500, "243040", False, False, "Segoe UI", "l", 1600),
                    ("• Aviso al cierre del día para inspección.", 1500, "243040", False, False, "Segoe UI", "l", 1200),
                    ("• Mínimas falsas alarmas al año.", 1500, "243040", False, False, "Segoe UI", "l", 1200),
                ],
            ),
        ],
        slide_num=2,
    )
    slides_xml.append(s2)
    notes_list.append([
        "LÁMINA 2 — GUION HABLADO (CONTEXTO Y PROBLEMA):",
        "• En una red como la RAMA (32 estaciones en la CDMX), el ozono tiene una varianza natural muy alta tanto entre horas del día como entre distintas zonas de la ciudad.",
        "• Cuando ocurre una falla de sensor, una descalibración o un ataque de integridad en la transmisión, los datos llegan al servidor central dentro de rangos físicamente posibles, por lo que un umbral fijo no los detecta.",
        "• El objetivo práctico es contar con un sistema de aviso temprano en el servidor central, sin aumentar el costo de la red ni instalar nodos redundantes, que indique al final del día si una estación requiere revisión.",
    ])

    # -------------------------------------------------------------------------
    # LÁMINA 3: HIPÓTESIS Y OBJETIVOS
    # -------------------------------------------------------------------------
    s3 = wrap_slide(
        "F4F0E8",
        header_shapes("HIPÓTESIS Y OBJETIVOS", "Contraste espacio-temporal sin aumentar el costo de la red")
        + [
            xml_card(
                4, x0, 1380000, 11064240, 1350000, "172540", "172540",
                [
                    ("HIPÓTESIS CENTRAL", 1300, "C8641E", True, False, "Segoe UI", "l", 0),
                    ("Contrastar cada estación contra su historial reciente y sus estaciones vecinas permite detectar anomalías sutiles de integridad manteniendo una tasa baja de falsas alarmas.", 1750, "FFFFFF", False, False, "Segoe UI", "l", 800),
                ],
            ),
            xml_card(
                5, x0, 3050000, cw, 3050000, "FFFFFF", "0F4C81",
                [
                    ("Objetivo 1 · Viabilidad", 1800, "0F4C81", True, False, "Segoe UI", "l", 0),
                    ("Bajas falsas alarmas", 1600, "1B2A4A", True, False, "Segoe UI", "l", 1400),
                    ("Operar en ~1% nominal (~3.6 a 5 días/año por estación) con alta sensibilidad (Recall).", 1450, "243040", False, False, "Segoe UI", "l", 1200),
                ],
            ),
            xml_card(
                6, x0 + cw + gap, 3050000, cw, 3050000, "FFFFFF", "D97724",
                [
                    ("Objetivo 2 · Robustez", 1800, "D97724", True, False, "Segoe UI", "l", 0),
                    ("Vecinas y sesgo lento", 1600, "1B2A4A", True, False, "Segoe UI", "l", 1400),
                    ("Resistir ataques coordinados en estaciones vecinas y sesgos sostenidos de varias semanas.", 1450, "243040", False, False, "Segoe UI", "l", 1200),
                ],
            ),
            xml_card(
                7, x0 + 2 * (cw + gap), 3050000, cw, 3050000, "FFFFFF", "7B3294",
                [
                    ("Objetivo 3 · Imágenes TINTO", 1800, "7B3294", True, False, "Segoe UI", "l", 0),
                    ("Transformación tabular → 2D", 1600, "1B2A4A", True, False, "Segoe UI", "l", 1400),
                    ("Evaluar imágenes sintéticas TINTO (estación-día) con redes convolucionales y contexto temporal.", 1450, "243040", False, False, "Segoe UI", "l", 1200),
                ],
            ),
        ],
        slide_num=3,
    )
    slides_xml.append(s3)
    notes_list.append([
        "LÁMINA 3 — GUION HABLADO (HIPÓTESIS Y OBJETIVOS):",
        "• Nuestra hipótesis parte de que una estación aislada no basta para distinguir entre una contingencia ambiental real y una anomalía del sensor; hace falta contrastar contra su propio pasado inmediato y contra las estaciones vecinas.",
        "• Buscamos tres cosas: (1) que el número de falsas alarmas al año sea suficientemente bajo para ser operable (~4–5 días al año), (2) medir hasta dónde resiste el detector si se comprometen vecinas o si el sesgo dura semanas, y (3) explorar la transformación de series tabulares a imágenes mediante TINTO.",
    ])

    # -------------------------------------------------------------------------
    # LÁMINA 4: ESCENARIOS DE ANOMALÍA Y MODELO DE AMENAZA
    # -------------------------------------------------------------------------
    s4 = wrap_slide(
        "FFFFFF",
        header_shapes("MODELO DE AMENAZA Y EXPERIMENTOS", "Cuatro escenarios evaluados sobre mediciones reales de O₃")
        + [
            xml_table(
                4,
                548640,
                1420000,
                11064240,
                4550000,
                [2700000, 3164240, 2900000, 2300000],
                ["Escenario", "Formulación", "Magnitudes evaluadas", "Duración"],
                [
                    ["1. Anomalía proporcional (δ%)", "x'(t) = x(t) · (1 ± δ)", "δ = 20%, 50%, 100%", "Episodios de 3, 5 y 7 días"],
                    ["2. Escalón aditivo fijo (ppb)", "x'(t) = x(t) + A", "+10, +20, +40 ppb", "Episodios de 3, 5 y 7 días"],
                    ["3. Ataque coordinado a vecinas", "Estación s + k vecinas alteradas", "0, 1, 2 y 4 vecinas", "Episodios de 3, 5 y 7 días"],
                    ["4. Sesgo lento / sostenido", "Desplazamiento constante", "+20 ppb continuos", "8 semanas (56 días)"],
                ],
            )
        ],
        slide_num=4,
    )
    slides_xml.append(s4)
    notes_list.append([
        "LÁMINA 4 — GUION HABLADO (ESCENARIOS DE ANOMALÍA):",
        "• Probamos cuatro tipos de anomalías sobre los datos reales:",
        "  1) Cambios proporcionales (20%, 50% y 100%) hacia arriba o hacia abajo.",
        "  2) Escalones aditivos fijos (+10, +20 y +40 ppb), que representan descalibraciones o sesgos constantes.",
        "  3) Ataques coordinados donde, además de la estación evaluada, también se alteran simultáneamente 1, 2 o las 4 estaciones vecinas.",
        "  4) Un sesgo sostenido durante 8 semanas seguidas para evaluar cuándo la ventana histórica termina absorbiendo la anomalía.",
    ])

    # -------------------------------------------------------------------------
    # LÁMINAS 5 A 11: DIAGRAMAS Y GRÁFICAS EN ALTA RESOLUCIÓN
    # -------------------------------------------------------------------------
    img_slides_spec = [
        (
            5,
            "ARQUITECTURA DEL DETECTOR PROPUESTO",
            "Ensamble vecinal con filtro: ventana de 48 h y decisión diaria",
            "diag1_arquitectura_detector.png",
            (1850, 680),
            "6 características por hora (48 h) · El filtro descarta hasta 2 vecinas que se desvíen junto con s (τ = 0.26σ) · Alerta diaria en p99.",
            [
                "LÁMINA 5 — GUION HABLADO (ARQUITECTURA DEL DETECTOR):",
                "• Columna 1 (Entradas): Para cada estación s tomamos sus lecturas horarias de O3, las de sus 4 vecinas más cercanas y su propio perfil de los últimos 14 días.",
                "• Columna 2 (Filtro vecinal): Antes de calcular la referencia espacial, verificamos si alguna vecina presenta el mismo salto que s (umbral τ = 0.26σ). Si es así, se excluye como sospechosa (máximo 2 vecinas) y la mediana limpia se calcula con las restantes.",
                "• Columna 3 (Ventana 48h × 6): Construimos la matriz con el O3 propio, hora del día (seno/coseno), residuo frente a sus 14 días y contraste frente a la mediana vecinal limpia.",
                "• Columna 4 y 5 (Ensamble y Decisión): Cinco redes LSTM promedian su puntaje horario; al cierre del día se toma el máximo de las 24 horas y se compara contra el umbral p99.",
            ],
        ),
        (
            6,
            "PROTOCOLO EXPERIMENTAL (2017 – 2026)",
            "Separación estricta de bloques anuales sin fuga de información",
            "diag2_particion_temporal.png",
            (1850, 560),
            "10 años de la RAMA (32 estaciones) · Pesos entrenados en 2020–2021 · Umbral p99 fijado una sola vez en 2023 limpio (9,097 estación-días).",
            [
                "LÁMINA 6 — GUION HABLADO (PARTICIÓN TEMPORAL 2017–2026):",
                "• Para evitar cualquier fuga de información hacia el futuro o hacia el pasado, dividimos los 10 años en bloques estrictos:",
                "  - 2020–2021: Entrenamiento de los pesos de las 5 redes LSTM (y del PCA/MinMax en TINTO).",
                "  - 2022: Selección de diseño y del umbral del filtro de vecinas (τ = 0.26σ).",
                "  - 2023 limpio: Calibración única del umbral de falsa alarma (p99 = 0.1508).",
                "  - 2024–jul 2026: Banco de pruebas con 30 calendarios de ataque.",
                "  - ago–sep 2026: Prueba de despliegue real con 60 días crudos de SINAICA en arranque en frío (sin historia previa al día 1).",
            ],
        ),
        (
            7,
            "ELECCIÓN DEL PUNTO DE OPERACIÓN",
            "Sensibilidad (Recall) frente a días con falsas alarmas al año",
            "fig1_punto_operacion.png",
            (1850, 920),
            "En p99 (~3.6 días/año nominales; 4.7 días/año en banco) se duplica el Recall frente a p99.9 sin disparar las falsas alarmas como p95 (18 días/año).",
            [
                "LÁMINA 7 — GUION HABLADO (PUNTO DE OPERACIÓN p99):",
                "• En la práctica, una alarma al final del día significa enviar personal o revisar la estación; por eso medimos el costo en días de falsa alarma al año (de 365).",
                "• En el Panel A comparamos p99.9, p99, p98 y p95: p99 alcanza 91% de Recall en δ=50% y 98% en δ=100% con ~3.6 días/año nominales.",
                "• En el Panel B (banco 2024–2026) vemos que usar p99.9 (azul claro) pierde la mitad de las anomalías moderadas (0.40 vs 0.80 en δ=50% y 0.44 vs 0.83 en +20 ppb). Por eso fijamos p99 en adelante.",
            ],
        ),
        (
            8,
            "RESULTADOS · UNA ESTACIÓN ATACADA (UMBRAL p99)",
            "Sensibilidad (Recall) en anomalías proporcionales (%), fijas (ppb) y despliegue",
            "fig2_una_estacion_p99.png",
            (1850, 930),
            "Con δ ≥ 50% y ≥ 20 ppb, el Ensamble vecinal con filtro alcanza Recall de 0.80–0.96 en banco y 0.91–0.98 en despliegue (F1 = 0.80).",
            [
                "LÁMINA 8 — GUION HABLADO (1 ESTACIÓN ATACADA EN p99):",
                "• Comparamos directamente nuestro detector final (azul oscuro) contra PARAAD-SA (verde) y los dos pilotos exploratorios de TINTO (morado: 1 día; naranja: 7 días).",
                "• En δ=50% y +20 ppb nuestro detector supera el 80% de Recall (frente a 36% y 57% de PARAAD-SA), y en los 60 días de despliegue alcanza 91% y 98%.",
                "• En el Panel B (+40 ppb) destaca que cuando a TINTO se le agregan los 7 días previos como contexto temporal (barra naranja), su Recall sube de 0.02 a 1.00.",
            ],
        ),
        (
            9,
            "RESULTADOS · ATAQUE COORDINADO A VECINAS (UMBRAL p99)",
            "Sensibilidad según el número de estaciones vecinas comprometidas (0 a 4)",
            "fig3_ataque_coordinado_p99.png",
            (1850, 920),
            "Con 1 vecina comprometida el filtro sostiene Recall de 0.56–0.62 (superando a PARAAD-SA y TINTO); cegar al detector exige comprometer ≥ 3 vecinas.",
            [
                "LÁMINA 9 — GUION HABLADO (ATAQUE COORDINADO A VECINAS):",
                "• Evaluamos de 0 a 4 vecinas comprometidas simultáneamente en escala uniforme.",
                "• Con 0 y 1 vecina atacada, el Ensamble vecinal con filtro supera claramente a PARAAD-SA y TINTO.",
                "• Las líneas de PARAAD-SA (verde) y TINTO (naranja) son horizontales porque no usan estaciones vecinas: no se ven afectadas cuando se atacan vecinas, pero parten de un Recall mucho menor y PARAAD-SA tiene el doble de falsas alarmas (9.6 vs 4.7 días/año).",
            ],
        ),
        (
            10,
            "RESULTADOS · SESGO SOSTENIDO DE LARGO PLAZO (UMBRAL p99)",
            "Horizonte de detección durante 8 semanas continuas (+20 ppb)",
            "fig4_sesgo_sostenido_p99.png",
            (1750, 880),
            "Sin vecinas (naranja) el detector se adapta en la Semana 2; la referencia vecinal (azul) sostiene la alerta durante 4 semanas (Recall medio = 76%).",
            [
                "LÁMINA 10 — GUION HABLADO (SESGO SOSTENIDO DE 8 SEMANAS):",
                "• Ante un escalón continuo de +20 ppb durante 8 semanas, el modelo que solo usa la historia propia (naranja) absorbe el error en su perfil de 14 días y cae a 21% en la semana 2 y a 1% en la semana 3.",
                "• En cambio, al contrastar contra las estaciones vecinas (azul), nuestro detector mantiene la detección durante 4 semanas completas (Recall promedio de 76%), dando un mes entero de margen antes de que la normalización móvil de 30 días absorba el sesgo.",
            ],
        ),
        (
            11,
            "EXPLORACIÓN CON IMÁGENES SINTÉTICAS TINTO",
            "De una imagen diaria aislada a contexto temporal de 7 días",
            "diag3_esquema_tinto.png",
            (1850, 620),
            "En mapas 32 × 32 las 24 horas se conservan sin colisión · Apilar 7 días previos eleva el Recall en +40 ppb de 1.7% a 100% y en δ=100% de 35.5% a 51.4%.",
            [
                "LÁMINA 11 — GUION HABLADO (EXPLORACIÓN TINTO):",
                "• Transformamos las 24 horas de cada estación-día en una imagen 32×32 con TINTO (PCA + MinMax ajustado en 2020–2021), comprobando que las 24 horas ocupan 24 píxeles distintos sin colisiones.",
                "• Con un Autoencoder de 1 solo día (arriba), un escalón fijo de +40 ppb pasa desapercibido (1.7% de Recall) porque parece simplemente un día de alto ozono.",
                "• Al darle como entrada los 7 días anteriores como canales para predecir el día objetivo (abajo), el Recall en +40 ppb sube a 100% y en δ=100% a 51.4%. El siguiente paso natural es integrar también a las estaciones vecinas en TINTO.",
            ],
        ),
    ]

    for s_num, tag, title, fname, (iw, ih), caption, notes in img_slides_spec:
        media_name = f"image_s{s_num}.png"
        media_map[s_num] = (media_name, IMG_DIR / fname)
        ix, iy, icx, icy = fit_image_box(iw, ih, 450000, 1180000, 11292000, 4880000)
        s_xml = wrap_slide(
            "FFFFFF",
            header_shapes(tag, title)
            + [
                xml_picture(10, "rId3", ix, iy, icx, icy),
                xml_textbox(
                    11, 548640, 6150000, 10500000, 420000,
                    [(caption, 1250, "243040", True, False, "Segoe UI", "l")],
                ),
            ],
            slide_num=s_num,
        )
        slides_xml.append(s_xml)
        notes_list.append(notes)

    # -------------------------------------------------------------------------
    # LÁMINA 12: CONCLUSIONES Y SIGUIENTES PASOS
    # -------------------------------------------------------------------------
    s12 = wrap_slide(
        "F4F0E8",
        header_shapes("CONCLUSIONES Y SIGUIENTES PASOS", "Síntesis de resultados y líneas abiertas")
        + [
            xml_card(
                4, x0, cy, cw, ch, "FFFFFF", "0F4C81",
                [
                    ("1. Detector validado", 1900, "0F4C81", True, False, "Segoe UI", "l", 0),
                    ("Ensamble vecinal con filtro", 1600, "1B2A4A", True, False, "Segoe UI", "l", 1800),
                    ("• Recall 80–98% (δ ≥ 50%, +20 ppb).", 1500, "243040", False, False, "Segoe UI", "l", 1600),
                    ("• ~4–5 días/año de falsas alarmas.", 1500, "243040", False, False, "Segoe UI", "l", 1200),
                    ("• Resiste 1–2 vecinas y 4 semanas.", 1500, "243040", False, False, "Segoe UI", "l", 1200),
                ],
            ),
            xml_card(
                5, x0 + cw + gap, cy, cw, ch, "FFFFFF", "D97724",
                [
                    ("2. Hallazgo central", 1900, "D97724", True, False, "Segoe UI", "l", 0),
                    ("Contexto espacio-temporal", 1600, "1B2A4A", True, False, "Segoe UI", "l", 1800),
                    ("• Indispensable en redes LSTM y en imágenes TINTO.", 1500, "243040", False, False, "Segoe UI", "l", 1600),
                    ("• En TINTO, 7 días previos llevan +40 ppb de 1.7% a 100%.", 1500, "243040", False, False, "Segoe UI", "l", 1200),
                ],
            ),
            xml_card(
                6, x0 + 2 * (cw + gap), cy, cw, ch, "FFFFFF", "1B9E77",
                [
                    ("3. Siguientes pasos (...)", 1900, "1B9E77", True, False, "Segoe UI", "l", 0),
                    ("Líneas abiertas", 1600, "1B2A4A", True, False, "Segoe UI", "l", 1800),
                    ("• Integrar estaciones vecinas en la representación TINTO.", 1500, "243040", False, False, "Segoe UI", "l", 1600),
                    ("• Esquemas ante compromiso de toda la vecindad (≥ 3 vecinas).", 1500, "243040", False, False, "Segoe UI", "l", 1200),
                    ("• ...", 1600, "1B9E77", True, False, "Segoe UI", "l", 1200),
                ],
            ),
        ],
        slide_num=12,
    )
    slides_xml.append(s12)
    notes_list.append([
        "LÁMINA 12 — GUION HABLADO (CONCLUSIONES Y SIGUIENTES PASOS):",
        "• Contamos con un detector de alerta temprana validado en 10 años de datos de la RAMA que opera con ~4–5 días de falsa alarma al año y alta sensibilidad.",
        "• Tanto en el modelo recurrente como en TINTO demostramos que el contexto temporal y espacial es la clave para separar anomalías de la varianza atmosférica.",
        "• Como siguientes pasos abiertos para retroalimentación y colaboración: llevar el contraste de estaciones vecinas hacia la representación TINTO y explorar esquemas híbridos cuando toda una vecindad es comprometida simultáneamente.",
    ])

    return slides_xml, media_map, notes_list


def empaquetar_pptx():
    slides_xml, media_map, notes_list = construir_diapositivas()
    n_slides = len(slides_xml)
    assert n_slides == 12

    with zipfile.ZipFile(TEMPLATE_PPTX, "r") as zin:
        with zipfile.ZipFile(OUT_PPTX, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            # Copiar todos los archivos base (excepto slides, notesSlides, media, presentation.xml y Content_Types)
            for item in zin.infolist():
                fn = item.filename
                if (
                    fn.startswith("ppt/slides/")
                    or fn.startswith("ppt/notesSlides/")
                    or fn.startswith("ppt/media/")
                    or fn in ("[Content_Types].xml", "ppt/presentation.xml", "ppt/_rels/presentation.xml.rels")
                ):
                    continue
                zout.writestr(item, zin.read(fn))

            # Escribir las 12 diapositivas y sus notas
            for idx in range(1, n_slides + 1):
                zout.writestr(f"ppt/slides/slide{idx}.xml", slides_xml[idx - 1].encode("utf8"))
                zout.writestr(f"ppt/notesSlides/notesSlide{idx}.xml", make_notes_xml(idx, notes_list[idx - 1]).encode("utf8"))

                # _rels de notesSlide
                notes_rel = (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    f'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="../slides/slide{idx}.xml"/>'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster" Target="../notesMasters/notesMaster1.xml"/>'
                    '</Relationships>'
                )
                zout.writestr(f"ppt/notesSlides/_rels/notesSlide{idx}.xml.rels", notes_rel.encode("utf8"))

                # _rels de slide
                img_rel = ""
                if idx in media_map:
                    m_name, m_path = media_map[idx]
                    zout.write(m_path, f"ppt/media/{m_name}")
                    img_rel = f'<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{m_name}"/>'

                slide_rel = (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    f'{img_rel}'
                    f'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide{idx}.xml"/>'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout7.xml"/>'
                    '</Relationships>'
                )
                zout.writestr(f"ppt/slides/_rels/slide{idx}.xml.rels", slide_rel.encode("utf8"))

            # ppt/presentation.xml (con 12 slides)
            sld_ids = "".join(f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, n_slides + 1))
            pres_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
                '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" saveSubsetFonts="1" autoCompressPictures="0">'
                '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
                '<p:notesMasterIdLst><p:notesMasterId r:id="rId17"/></p:notesMasterIdLst>'
                f'<p:sldIdLst>{sld_ids}</p:sldIdLst>'
                '<p:sldSz cx="12192000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/>'
                '</p:presentation>'
            )
            zout.writestr("ppt/presentation.xml", pres_xml.encode("utf8"))

            # ppt/_rels/presentation.xml.rels
            s_rels = "".join(
                f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
                for i in range(1, n_slides + 1)
            )
            pres_rels = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
                f'{s_rels}'
                '<Relationship Id="rId17" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster" Target="notesMasters/notesMaster1.xml"/>'
                '<Relationship Id="rId18" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/presProps" Target="presProps.xml"/>'
                '<Relationship Id="rId19" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/viewProps" Target="viewProps.xml"/>'
                '<Relationship Id="rId20" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>'
                '<Relationship Id="rId21" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/tableStyles" Target="tableStyles.xml"/>'
                '</Relationships>'
            )
            zout.writestr("ppt/_rels/presentation.xml.rels", pres_rels.encode("utf8"))

            # [Content_Types].xml
            ct_slides = "".join(
                f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                f'<Override PartName="/ppt/notesSlides/notesSlide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>'
                for i in range(1, n_slides + 1)
            )
            ct_layouts = "".join(
                f'<Override PartName="/ppt/slideLayouts/slideLayout{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
                for i in range(1, 12)
            )
            ct_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="jpeg" ContentType="image/jpeg"/>'
                '<Default Extension="png" ContentType="image/png"/>'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
                '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
                '<Override PartName="/ppt/notesMasters/notesMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml"/>'
                '<Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/>'
                '<Override PartName="/ppt/viewProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"/>'
                '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
                '<Override PartName="/ppt/theme/theme2.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
                '<Override PartName="/ppt/tableStyles.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml"/>'
                '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
                f'{ct_layouts}{ct_slides}</Types>'
            )
            zout.writestr("[Content_Types].xml", ct_xml.encode("utf8"))

    shutil.copy2(OUT_PPTX, ART_PPTX)
    print("Presentación creada con éxito en:", OUT_PPTX)


if __name__ == "__main__":
    empaquetar_pptx()
