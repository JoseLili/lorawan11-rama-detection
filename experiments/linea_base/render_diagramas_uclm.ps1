# Renderiza los 3 diagramas visuales con la misma estructura y MÍNIMO texto (solo palabras clave)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$outDir = Join-Path $root "docs\img\coloquio_uclm"
$artDir = "C:\Users\jose_\.gemini\antigravity\brain\69484fbb-153d-4dc8-bbe3-c46870f09661"

function New-Color([int]$r, [int]$g, [int]$b, [int]$a = 255) {
    return [System.Drawing.Color]::FromArgb($a, $r, $g, $b)
}

function New-RoundedRect([float]$x, [float]$y, [float]$w, [float]$h, [float]$r) {
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $d = $r * 2.0
    $path.AddArc($x, $y, $d, $d, 180, 90)
    $path.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
    $path.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
    $path.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
    $path.CloseFigure()
    return $path
}

function Fill-RoundedBox($g, [float]$x, [float]$y, [float]$w, [float]$h, [float]$r, $bgCol, $bdCol, [float]$bdW = 2.4) {
    $path = New-RoundedRect $x $y $w $h $r
    $b = New-Object System.Drawing.SolidBrush($bgCol)
    $p = New-Object System.Drawing.Pen($bdCol, $bdW)
    $g.FillPath($b, $path)
    $g.DrawPath($p, $path)
    $b.Dispose(); $p.Dispose(); $path.Dispose()
}

function Draw-Arrow($g, [float]$x1, [float]$y1, [float]$x2, [float]$y2, $col, [float]$w = 3.4) {
    $p = New-Object System.Drawing.Pen($col, $w)
    $dx = $x2 - $x1; $dy = $y2 - $y1
    $len = [Math]::Sqrt($dx*$dx + $dy*$dy)
    if ($len -lt 1) { $p.Dispose(); return }
    $ux = $dx / $len; $uy = $dy / $len
    $px = -$uy; $py = $ux
    $g.DrawLine($p, $x1, $y1, ($x2 - $ux*10), ($y2 - $uy*10))
    $pts = @(
        (New-Object System.Drawing.PointF($x2, $y2)),
        (New-Object System.Drawing.PointF(($x2 - $ux*14 + $px*7.5), ($y2 - $uy*14 + $py*7.5))),
        (New-Object System.Drawing.PointF(($x2 - $ux*14 - $px*7.5), ($y2 - $uy*14 - $py*7.5)))
    )
    $b = New-Object System.Drawing.SolidBrush($col)
    $g.FillPolygon($b, $pts)
    $p.Dispose(); $b.Dispose()
}

function Save-Both($bmp, [string]$filename) {
    $p1 = Join-Path $outDir $filename
    $p2 = Join-Path $artDir $filename
    $bmp.Save($p1, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Save($p2, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Output "Guardada: $p1"
}

$cAzul     = New-Color 15 76 129
$cAzulMed  = New-Color 36 105 166
$cAzulClar = New-Color 235 244 253
$cVerde    = New-Color 27 158 119
$cVerdeCl  = New-Color 236 250 245
$cNaranja  = New-Color 217 119 36
$cNarCl    = New-Color 255 247 236
$cRojo     = New-Color 196 58 49
$cRojoCl   = New-Color 253 238 236
$cMorado   = New-Color 110 55 140
$cMorCl    = New-Color 246 240 251
$cGrisOsc  = New-Color 70 82 96
$cGrisCl   = New-Color 245 247 250
$cTexto    = New-Color 28 35 43
$cSubtexto = New-Color 82 92 104
$cFondo    = New-Color 255 255 255

$fTitle    = New-Object System.Drawing.Font("Segoe UI", 26, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fStage    = New-Object System.Drawing.Font("Segoe UI", 15, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fBoxBig   = New-Object System.Drawing.Font("Segoe UI", 21, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fBoxTitle = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fBoxSub   = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fBody     = New-Object System.Drawing.Font("Segoe UI", 15, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)

$sfCenter = New-Object System.Drawing.StringFormat
$sfCenter.Alignment = [System.Drawing.StringAlignment]::Center
$sfCenter.LineAlignment = [System.Drawing.StringAlignment]::Center

$bTxt   = New-Object System.Drawing.SolidBrush($cTexto)
$bSub   = New-Object System.Drawing.SolidBrush($cSubtexto)
$bWhite = New-Object System.Drawing.SolidBrush($cFondo)
$bAzul  = New-Object System.Drawing.SolidBrush($cAzul)
$bNar   = New-Object System.Drawing.SolidBrush($cNaranja)
$bVer   = New-Object System.Drawing.SolidBrush($cVerde)
$bRoj   = New-Object System.Drawing.SolidBrush($cRojo)
$bMor   = New-Object System.Drawing.SolidBrush($cMorado)
$bGris  = New-Object System.Drawing.SolidBrush($cGrisOsc)

# ==============================================================================
# DIAGRAMA 1 (LÁMINA 5): Arquitectura del Ensamble vecinal con filtro (MÍNIMO TEXTO)
# ==============================================================================
$bmp = New-Object System.Drawing.Bitmap(1850, 680)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$g.Clear($cFondo)

$g.DrawString("Arquitectura del detector: Ensamble vecinal con filtro", $fTitle, $bTxt, 925, 42, $sfCenter)

# --- COLUMNA 1: ENTRADAS (x = 45..325) ---
$g.DrawString("1. ENTRADAS", $fStage, $bAzul, 185, 105, $sfCenter)

Fill-RoundedBox $g 45 135 280 115 12 $cAzulClar $cAzul
$g.DrawString("Estación objetivo (s)", $fBoxTitle, $bAzul, 185, 174, $sfCenter)
$g.DrawString("O₃ horario (ppb)", $fBody, $bSub, 185, 212, $sfCenter)

Fill-RoundedBox $g 45 285 280 150 12 $cNarCl $cNaranja
$g.DrawString("4 Estaciones vecinas", $fBoxTitle, $bNar, 185, 322, $sfCenter)
$vNames = @("v₁", "v₂", "v₃", "v₄")
for ($vi = 0; $vi -lt 4; $vi++) {
    $vx = 72 + $vi * 58
    Fill-RoundedBox $g $vx 358 48 48 8 $cFondo $cNaranja 2.0
    $g.DrawString($vNames[$vi], $fBoxSub, $bNar, ($vx + 24), 382, $sfCenter)
}

Fill-RoundedBox $g 45 470 280 115 12 $cGrisCl $cGrisOsc
$g.DrawString("Perfil propio", $fBoxTitle, $bGris, 185, 509, $sfCenter)
$g.DrawString("Últimos 14 días", $fBody, $bSub, 185, 547, $sfCenter)

# --- COLUMNA 2: FILTRO VECINAL (x = 385..695) ---
$g.DrawString("2. FILTRO VECINAL", $fStage, $bNar, 540, 105, $sfCenter)
Fill-RoundedBox $g 385 215 310 290 14 $cNarCl $cNaranja 2.4
$g.DrawString("Filtro (τ = 0.26σ)", $fBoxTitle, $bNar, 540, 255, $sfCenter)

Fill-RoundedBox $g 412 295 256 76 10 $cRojoCl $cRojo 1.8
$g.DrawString("✗ Excluye sospechosas", $fBoxSub, $bRoj, 540, 322, $sfCenter)
$g.DrawString("(máx. 2 vecinas)", $fBody, $bTxt, 540, 350, $sfCenter)

Fill-RoundedBox $g 412 395 256 80 10 $cVerdeCl $cVerde 1.8
$g.DrawString("✓ Mediana limpia", $fBoxSub, $bVer, 540, 422, $sfCenter)
$g.DrawString("Vecinas restantes", $fBody, $bTxt, 540, 452, $sfCenter)

Draw-Arrow $g 325 360 385 360 $cNaranja
Draw-Arrow $g 325 205 385 265 $cAzul

# --- COLUMNA 3: VENTANA (x = 755..1095) ---
$g.DrawString("3. VENTANA (48 h × 6)", $fStage, $bAzul, 925, 105, $sfCenter)
Fill-RoundedBox $g 755 135 340 450 14 $cAzulClar $cAzul 2.4
$g.DrawString("48 horas × 6 variables", $fBoxTitle, $bAzul, 925, 174, $sfCenter)

$feats = @(
    @{ n = "1. O₃ estación s";          c = $cAzul },
    @{ n = "2. Hora: sin(t)";           c = $cGrisOsc },
    @{ n = "3. Hora: cos(t)";           c = $cGrisOsc },
    @{ n = "4. Desvío vs. 14 días";     c = $cGrisOsc },
    @{ n = "5. Desvío vs. vecinas";     c = $cNaranja },
    @{ n = "6. Discrepancia vecinal";   c = $cNaranja }
)
for ($fi = 0; $fi -lt 6; $fi++) {
    $fy = 212 + $fi * 58
    Fill-RoundedBox $g 782 $fy 286 46 8 $cFondo $feats[$fi].c 1.8
    $bF = New-Object System.Drawing.SolidBrush($feats[$fi].c)
    $g.DrawString($feats[$fi].n, $fBoxSub, $bF, 925, ($fy + 23), $sfCenter)
    $bF.Dispose()
}

Draw-Arrow $g 325 180 755 180 $cAzul
Draw-Arrow $g 695 435 755 460 $cVerde
$pOrth = New-Object System.Drawing.Pen($cGrisOsc, 3.4)
$g.DrawLine($pOrth, 325, 535, 722, 535)
$g.DrawLine($pOrth, 722, 535, 722, 405)
$pOrth.Dispose()
Draw-Arrow $g 722 405 755 405 $cGrisOsc

# --- COLUMNA 4: ENSAMBLE 5 LSTM (x = 1155..1455) ---
$g.DrawString("4. MODELO PROFUNDO", $fStage, $bMor, 1305, 105, $sfCenter)
Fill-RoundedBox $g 1155 135 300 450 14 $cMorCl $cMorado 2.4
$g.DrawString("Ensamble (5 LSTM)", $fBoxTitle, $bMor, 1305, 174, $sfCenter)

for ($li = 1; $li -le 5; $li++) {
    $ly = 212 + ($li - 1) * 54
    Fill-RoundedBox $g 1185 $ly 240 42 8 $cFondo $cMorado 1.8
    $g.DrawString("LSTM #$li", $fBoxSub, $bMor, 1305, ($ly + 21), $sfCenter)
}

Fill-RoundedBox $g 1185 495 240 68 10 $cFondo $cAzul 2.0
$g.DrawString("Promedio p_s(t)", $fBoxSub, $bAzul, 1305, 529, $sfCenter)

Draw-Arrow $g 1095 360 1155 360 $cAzul

# --- COLUMNA 5: ALERTA DIARIA (x = 1515..1805) ---
$g.DrawString("5. DECISIÓN DIARIA", $fStage, $bVer, 1660, 105, $sfCenter)
Fill-RoundedBox $g 1515 135 290 450 14 $cVerdeCl $cVerde 2.4
$g.DrawString("Cierre del día", $fBoxTitle, $bVer, 1660, 174, $sfCenter)

Fill-RoundedBox $g 1542 215 236 86 10 $cFondo $cVerde 1.8
$g.DrawString("Máximo 24 horas", $fBody, $bSub, 1660, 242, $sfCenter)
$g.DrawString("S = max p_s(t)", $fBoxTitle, $bVer, 1660, 274, $sfCenter)

Fill-RoundedBox $g 1542 325 236 90 10 $cNarCl $cNaranja 1.8
$g.DrawString("Umbral p99", $fBoxSub, $bNar, 1660, 353, $sfCenter)
$g.DrawString("S > 0.1508", $fBoxTitle, $bTxt, 1660, 386, $sfCenter)

Fill-RoundedBox $g 1542 440 236 115 10 $cVerde $cVerde 2.0
$g.DrawString("ALERTA", $fBoxBig, $bWhite, 1660, 480, $sfCenter)
$g.DrawString("TEMPRANA", $fBoxBig, $bWhite, 1660, 514, $sfCenter)

Draw-Arrow $g 1455 360 1515 360 $cVerde

Save-Both $bmp "diag1_arquitectura_detector.png"

# ==============================================================================
# DIAGRAMA 2 (LÁMINA 6): Línea del Tiempo 2017–2026 (MÍNIMO TEXTO)
# ==============================================================================
$bmp2 = New-Object System.Drawing.Bitmap(1850, 560)
$g2 = [System.Drawing.Graphics]::FromImage($bmp2)
$g2.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g2.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$g2.Clear($cFondo)

$g2.DrawString("Partición temporal sin fuga de información (2017 – 2026)", $fTitle, $bTxt, 925, 42, $sfCenter)

$tlY = 145.0
$pLine = New-Object System.Drawing.Pen((New-Color 180 195 210), 7.0)
$g2.DrawLine($pLine, 120.0, $tlY, 1730.0, $tlY)

$blocks = @(
    @{ yr = "2017 – 2019"; title = "Examen Histórico"; col = $cGrisOsc; bg = $cGrisCl;   mid = "Fuera de muestra"; badge = "Reserva ciega" },
    @{ yr = "2020 – 2021"; title = "Entrenamiento";    col = $cAzul;    bg = $cAzulClar; mid = "5 redes LSTM";     badge = "Congela pesos" },
    @{ yr = "2022";        title = "Selección";        col = $cAzulMed; bg = $cAzulClar; mid = "Filtro τ = 0.26σ"; badge = "Congela diseño" },
    @{ yr = "2023";        title = "Calibración";      col = $cNaranja; bg = $cNarCl;    mid = "Datos limpios";    badge = "Fija umbral p99" },
    @{ yr = "2024 – 2026"; title = "Banco de Pruebas"; col = $cMorado;  bg = $cMorCl;    mid = "30 calendarios";   badge = "Evaluación" },
    @{ yr = "ago – sep 26";title = "Despliegue";       col = $cVerde;   bg = $cVerdeCl;  mid = "Arranque en frío"; badge = "60 días crudos" }
)

$bw = 272.0; $bh = 285.0; $by = 195.0; $bgap = 22.0; $bx0 = 48.0

for ($i = 0; $i -lt 6; $i++) {
    $cx = $bx0 + $i * ($bw + $bgap)
    $mx = $cx + $bw / 2.0
    $bl = $blocks[$i]
    $bCol = New-Object System.Drawing.SolidBrush($bl.col)

    $g2.FillEllipse($bWhite, ($mx - 18), ($tlY - 18), 36, 36)
    $g2.FillEllipse($bCol,   ($mx - 12), ($tlY - 12), 24, 24)
    $g2.DrawString($bl.yr, $fBoxTitle, $bCol, $mx, ($tlY - 38), $sfCenter)

    Fill-RoundedBox $g2 $cx $by $bw $bh 14 $bl.bg $bl.col 2.4
    $pathTop = New-RoundedRect $cx $by $bw 58 14
    $g2.FillPath($bCol, $pathTop)
    $g2.FillRectangle($bCol, $cx, ($by + 44), $bw, 14)
    $g2.DrawString($bl.title, $fBoxTitle, $bWhite, $mx, ($by + 29), $sfCenter)

    # Palabra clave central grande
    $g2.DrawString($bl.mid, $fBoxBig, $bTxt, $mx, ($by + 135), $sfCenter)

    # Insignia inferior
    Fill-RoundedBox $g2 ($cx + 22) ($by + $bh - 68) ($bw - 44) 48 10 $bl.col $bl.col 1.0
    $g2.DrawString($bl.badge, $fBoxSub, $bWhite, $mx, ($by + $bh - 44), $sfCenter)

    if ($i -ge 1 -and $i -lt 5) {
        Draw-Arrow $g2 ($cx + $bw + 2) ($by + $bh/2) ($cx + $bw + $bgap - 2) ($by + $bh/2) $cAzul
    }
    $bCol.Dispose(); $pathTop.Dispose()
}

Save-Both $bmp2 "diag2_particion_temporal.png"

# ==============================================================================
# DIAGRAMA 3 (LÁMINA 11): Esquema TINTO (MÍNIMO TEXTO)
# ==============================================================================
$bmp3 = New-Object System.Drawing.Bitmap(1850, 620)
$g3 = [System.Drawing.Graphics]::FromImage($bmp3)
$g3.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g3.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$g3.Clear($cFondo)

$g3.DrawString("Exploración TINTO: de 1 día aislado a contexto temporal (7 días)", $fTitle, $bTxt, 925, 42, $sfCenter)

# Bloque Izquierdo: Codificación TINTO
Fill-RoundedBox $g3 55 110 440 445 14 $cAzulClar $cAzul 2.4
$g3.DrawString("1. Imagen TINTO (32 × 32)", $fBoxTitle, $bAzul, 275, 152, $sfCenter)

Fill-RoundedBox $g3 90 195 370 100 10 $cFondo $cAzul 1.8
$g3.DrawString("24 horas de O₃", $fBoxBig, $bTxt, 275, 232, $sfCenter)
$g3.DrawString("[h₀₀ ... h₂₃]", $fBody, $bSub, 275, 268, $sfCenter)

Draw-Arrow $g3 275 295 275 345 $cAzul

Fill-RoundedBox $g3 90 345 370 165 10 $cFondo $cAzul 1.8
$g3.DrawString("Mapa PCA + MinMax", $fBoxBig, $bAzul, 275, 395, $sfCenter)
$g3.DrawString("24 píxeles fijos", $fBoxSub, $bVer, 275, 440, $sfCenter)
$g3.DrawString("(0 colisiones)", $fBody, $bSub, 275, 472, $sfCenter)

# Bloque Superior Derecho: Autoencoder 1 día
Fill-RoundedBox $g3 575 110 1220 200 14 $cMorCl $cMorado 2.4
$g3.DrawString("A. Autoencoder Convolucional (1 solo día)", $fBoxTitle, $bMor, 1185, 146, $sfCenter)

Fill-RoundedBox $g3 610 180 340 100 10 $cFondo $cMorado 1.8
$g3.DrawString("Entrada: Día d", $fBoxBig, $bMor, 780, 218, $sfCenter)
$g3.DrawString("(sin días previos)", $fBody, $bSub, 780, 252, $sfCenter)

Draw-Arrow $g3 950 230 1020 230 $cMorado

Fill-RoundedBox $g3 1020 180 740 100 10 $cFondo $cMorado 1.8
$g3.DrawString("Recall (p99)", $fBoxSub, $bSub, 1390, 208, $sfCenter)
$g3.DrawString("δ = 100%: 35.5%     |     +40 ppb: 1.7%", $fBoxBig, $bMor, 1390, 248, $sfCenter)

# Bloque Inferior Derecho: Predictor Temporal 7 días
Fill-RoundedBox $g3 575 355 1220 200 14 $cNarCl $cNaranja 2.4
$g3.DrawString("B. Predictor CNN Temporal (7 días previos)", $fBoxTitle, $bNar, 1185, 391, $sfCenter)

Fill-RoundedBox $g3 610 425 340 100 10 $cFondo $cNaranja 1.8
$g3.DrawString("Entrada: 7 días previos", $fBoxBig, $bNar, 780, 463, $sfCenter)
$g3.DrawString("[d−7 ... d−1] → predice día d", $fBody, $bTxt, 780, 497, $sfCenter)

Draw-Arrow $g3 950 475 1020 475 $cNaranja

Fill-RoundedBox $g3 1020 425 740 100 10 $cFondo $cNaranja 1.8
$g3.DrawString("Recall (p99)", $fBoxSub, $bSub, 1390, 453, $sfCenter)
$g3.DrawString("δ = 100%: 51.4%     |     +40 ppb: 100.0%", $fBoxBig, $bNar, 1390, 493, $sfCenter)

Draw-Arrow $g3 495 280 575 215 $cMorado
Draw-Arrow $g3 495 380 575 455 $cNaranja

Save-Both $bmp3 "diag3_esquema_tinto.png"
