# Renderiza las 4 figuras de la presentación (UCLM / Coloquio PCIC) en alta resolución (PNG)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$outDir = Join-Path $root "docs\img\coloquio_uclm"
$artDir = "C:\Users\jose_\.gemini\antigravity\brain\69484fbb-153d-4dc8-bbe3-c46870f09661"
$datos = Get-Content (Join-Path $outDir "datos_graficas.json") -Raw -Encoding UTF8 | ConvertFrom-Json

function New-Color([int]$r, [int]$g, [int]$b, [int]$a = 255) {
    return [System.Drawing.Color]::FromArgb($a, $r, $g, $b)
}

# Paleta armónica consistente
$cAzul     = New-Color 15 76 129      # Ensamble vecinal con filtro (final)
$cAzulClar = New-Color 66 139 202     # Umbral p99.9 / TINTO AE
$cVerde    = New-Color 27 158 119     # PARAAD-SA / δ=100%
$cNaranja  = New-Color 217 119 36     # TINTO Temporal-7d / δ=20%
$cMorado   = New-Color 123 50 148     # TINTO Autoencoder
$cTexto    = New-Color 28 35 43
$cSubtexto = New-Color 82 92 104
$cGrid     = New-Color 224 229 235
$cBorde    = New-Color 175 184 195
$cFondo    = New-Color 255 255 255
$cPanelBg  = New-Color 250 251 253
$cResalte  = New-Color 254 246 230
$cHeaderBg = New-Color 238 242 247

$fTitle    = New-Object System.Drawing.Font("Segoe UI", 22, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fSubtitle = New-Object System.Drawing.Font("Segoe UI", 15, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$fPanel    = New-Object System.Drawing.Font("Segoe UI", 17, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fAxisLbl  = New-Object System.Drawing.Font("Segoe UI", 15, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fTick     = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$fTickBold = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fVal      = New-Object System.Drawing.Font("Segoe UI", 13, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fLegend   = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$fNote     = New-Object System.Drawing.Font("Segoe UI", 13, [System.Drawing.FontStyle]::Italic, [System.Drawing.GraphicsUnit]::Pixel)

$sfCenter = New-Object System.Drawing.StringFormat
$sfCenter.Alignment = [System.Drawing.StringAlignment]::Center
$sfCenter.LineAlignment = [System.Drawing.StringAlignment]::Center

$sfRight = New-Object System.Drawing.StringFormat
$sfRight.Alignment = [System.Drawing.StringAlignment]::Far
$sfRight.LineAlignment = [System.Drawing.StringAlignment]::Center

$sfLeft = New-Object System.Drawing.StringFormat
$sfLeft.Alignment = [System.Drawing.StringAlignment]::Near
$sfLeft.LineAlignment = [System.Drawing.StringAlignment]::Center

function Init-Canvas([int]$w, [int]$h) {
    $bmp = New-Object System.Drawing.Bitmap($w, $h)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
    $g.Clear($cFondo)
    return @{ bmp = $bmp; g = $g }
}

function Save-Both($bmp, [string]$filename) {
    $p1 = Join-Path $outDir $filename
    $p2 = Join-Path $artDir $filename
    $bmp.Save($p1, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Save($p2, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Output "Guardada: $p1"
}

function Draw-RotatedYLabel($g, [string]$text, [float]$x, [float]$y) {
    $state = $g.Save()
    $g.TranslateTransform($x, $y)
    $g.RotateTransform(-90)
    $b = New-Object System.Drawing.SolidBrush($cTexto)
    $g.DrawString($text, $fAxisLbl, $b, 0, 0, $sfCenter)
    $b.Dispose()
    $g.Restore($state)
}

function Draw-YGridAndAxis($g, [float]$px, [float]$py, [float]$pw, [float]$ph, [string]$yTitle) {
    $bPanel = New-Object System.Drawing.SolidBrush($cPanelBg)
    $g.FillRectangle($bPanel, $px, $py, $pw, $ph)
    $bPanel.Dispose()

    $pGrid = New-Object System.Drawing.Pen($cGrid, 1.2)
    $pAxis = New-Object System.Drawing.Pen($cBorde, 1.8)
    $bTick = New-Object System.Drawing.SolidBrush($cTexto)

    # Escala armónica de 0.2 en 0.2: 0.0, 0.2, 0.4, 0.6, 0.8, 1.0
    for ($i = 0; $i -le 5; $i++) {
        $val = $i * 0.2
        $yy = $py + $ph - ($val * $ph)
        $g.DrawLine($pGrid, $px, $yy, $px + $pw, $yy)
        $lbl = $val.ToString("0.0", [System.Globalization.CultureInfo]::InvariantCulture)
        $g.DrawString($lbl, $fTick, $bTick, $px - 10, $yy, $sfRight)
    }
    $g.DrawRectangle($pAxis, $px, $py, $pw, $ph)
    Draw-RotatedYLabel $g $yTitle ($px - 52) ($py + $ph / 2.0)

    $pGrid.Dispose()
    $pAxis.Dispose()
    $bTick.Dispose()
}

function Draw-SeriesCustom($g, $xs, $vals, $py, $ph, $color, [bool]$dashed, $dyList) {
    $pen = New-Object System.Drawing.Pen($color, 3.4)
    if ($dashed) { $pen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash }
    $brush = New-Object System.Drawing.SolidBrush($color)
    $wBrush = New-Object System.Drawing.SolidBrush($cFondo)
    $pts = @()
    for ($i = 0; $i -lt $xs.Count; $i++) {
        $yy = $py + $ph - ([float]$vals[$i] * $ph)
        $pts += New-Object System.Drawing.PointF([float]$xs[$i], [float]$yy)
    }
    for ($i = 0; $i -lt ($pts.Count - 1); $i++) {
        $g.DrawLine($pen, $pts[$i], $pts[$i+1])
    }
    for ($i = 0; $i -lt $pts.Count; $i++) {
        $g.FillEllipse($wBrush, $pts[$i].X - 6.5, $pts[$i].Y - 6.5, 13, 13)
        $g.FillEllipse($brush, $pts[$i].X - 4.8, $pts[$i].Y - 4.8, 9.6, 9.6)
        $vStr = ([float]$vals[$i]).ToString("0.00", [System.Globalization.CultureInfo]::InvariantCulture)
        $dy = [float]$dyList[$i]
        $g.DrawString($vStr, $fVal, $brush, $pts[$i].X, ($pts[$i].Y + $dy), $sfCenter)
    }
    $pen.Dispose(); $brush.Dispose(); $wBrush.Dispose()
}

$bTxt = New-Object System.Drawing.SolidBrush($cTexto)
$bSub = New-Object System.Drawing.SolidBrush($cSubtexto)
$pVGrid = New-Object System.Drawing.Pen($cGrid, 1.0)

# ==============================================================================
# GRÁFICA 1 (LÁMINA 7): Solo Sensibilidad (Recall) vs. días con falsas alarmas
# Sin líneas punteadas ni métricas mezcladas: eje Y = únicamente Recall
# ==============================================================================
$cv = Init-Canvas 1850 920
$g = $cv.g

$g.DrawString("Elección del punto de operación: Sensibilidad (Recall) vs. días con falsas alarmas al año", $fTitle, $bTxt, 925, 32, $sfCenter)
$g.DrawString("Detector final: Ensamble vecinal con filtro · Efecto del umbral (p99.9 a p95) sobre la sensibilidad en anomalías proporcionales (%) y fijas (ppb)", $fSubtitle, $bSub, 925, 64, $sfCenter)

# Panel A (Izquierda): Curva de Recall en los 4 percentiles (p99.9, p99, p98, p95)
$p1x = 110; $p1y = 155; $p1w = 760; $p1h = 550
Draw-YGridAndAxis $g $p1x $p1y $p1w $p1h "Sensibilidad (Recall) [escala 0.0 a 1.0]"
$g.DrawString("A. Sensibilidad (Recall) según el umbral y días de falsa alarma al año", $fPanel, $bTxt, ($p1x + $p1w/2), ($p1y - 28), $sfCenter)

$xs1 = @(0, 1, 2, 3) | ForEach-Object { $p1x + 95 + $_ * (($p1w - 190) / 3.0) }
$bHi = New-Object System.Drawing.SolidBrush($cResalte)
$g.FillRectangle($bHi, [float]($xs1[1] - 62), [float]($p1y + 2), 124.0, [float]($p1h - 4))
$bHi.Dispose()

for ($i = 0; $i -lt 4; $i++) {
    $xx = $xs1[$i]
    $g.DrawLine($pVGrid, $xx, $p1y, $xx, $p1y + $p1h)
    $row = $datos.g1_desp[$i]
    $fontUse = if ($i -eq 1) { $fTickBold } else { $fTick }
    $g.DrawString($row.percentil, $fontUse, $bTxt, $xx, $p1y + $p1h + 22, $sfCenter)
    $g.DrawString("Nominal: $($row.dias_fa_nominal) d/año", $fTick, $bSub, $xx, $p1y + $p1h + 44, $sfCenter)
    $g.DrawString("(Observado: $($row.dias_fa_real) d/año)", $fNote, $bSub, $xx, $p1y + $p1h + 64, $sfCenter)
}
$g.DrawString("Umbral de operación (percentil en 2023 limpio y días de falsa alarma por estación al año)", $fAxisLbl, $bTxt, ($p1x + $p1w/2), ($p1y + $p1h + 98), $sfCenter)

$vR100 = $datos.g1_desp | ForEach-Object { $_.recall_d100 }
$vR50  = $datos.g1_desp | ForEach-Object { $_.recall_d50 }
$vR20  = $datos.g1_desp | ForEach-Object { $_.recall_d20 }

# Únicamente las 3 curvas sólidas de Recall (δ = 100%, δ = 50%, δ = 20%)
Draw-SeriesCustom $g $xs1 $vR100 $p1y $p1h $cVerde   $false @(-16, -16, -16, -16)
Draw-SeriesCustom $g $xs1 $vR50  $p1y $p1h $cAzul    $false @( 17,  17,  17,  17)
Draw-SeriesCustom $g $xs1 $vR20  $p1y $p1h $cNaranja $false @(-16, -16, -16, -16)

# Etiqueta del punto elegido p99 en zona limpia
$bBadgeBg = New-Object System.Drawing.SolidBrush((New-Color 255 248 235 240))
$pBadgeBd = New-Object System.Drawing.Pen($cNaranja, 1.5)
$g.FillRectangle($bBadgeBg, [float]($xs1[1] - 110), [float]($p1y + 240), 220.0, 46.0)
$g.DrawRectangle($pBadgeBd, [float]($xs1[1] - 110), [float]($p1y + 240), 220.0, 46.0)
$bBadge = New-Object System.Drawing.SolidBrush($cNaranja)
$g.DrawString("Punto elegido: p99 (~3.6 d/año)", $fTickBold, $bBadge, $xs1[1], ($p1y + 253), $sfCenter)
$g.DrawString("Recall = 91% (δ=50%) y 98% (δ=100%)", $fVal, $bTxt, $xs1[1], ($p1y + 272), $sfCenter)
$bBadge.Dispose(); $bBadgeBg.Dispose(); $pBadgeBd.Dispose()

# Panel B (Derecha): Solo Sensibilidad (Recall) en Banco (2024–2026) por magnitud (% y ppb) en p99.9 vs p99
$p2x = 980; $p2y = 155; $p2w = 790; $p2h = 550
Draw-YGridAndAxis $g $p2x $p2y $p2w $p2h "Sensibilidad (Recall) [escala 0.0 a 1.0]"
$g.DrawString("B. Sensibilidad (Recall) en banco (2024–2026): p99.9 vs. p99 (% y ppb fijo)", $fPanel, $bTxt, ($p2x + $p2w/2), ($p2y - 28), $sfCenter)

$bHdr = New-Object System.Drawing.SolidBrush($cHeaderBg)
$g.FillRectangle($bHdr, [float]($p2x + 1), [float]($p2y - 1), [float]($p2w - 2), 28.0)
$bHdr.Dispose()

$lblsTam = @("δ = 20%", "δ = 50%", "δ = 100%", "+10 ppb", "+20 ppb", "+40 ppb")
$rec999 = $datos.g1_banco."p99.9".recall
$rec99  = $datos.g1_banco."p99".recall

$step2 = $p2w / 6.0
$bw = 38.0
$b999 = New-Object System.Drawing.SolidBrush($cAzulClar)
$b99  = New-Object System.Drawing.SolidBrush($cAzul)

$xSep = $p2x + 3 * $step2
$pSep = New-Object System.Drawing.Pen($cBorde, 1.5)
$pSep.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
$g.DrawLine($pSep, $xSep, $p2y, $xSep, $p2y + $p2h)
$g.DrawString("Anomalías proporcionales (δ%)", $fTickBold, $bSub, ($p2x + 1.5 * $step2), ($p2y + 13), $sfCenter)
$g.DrawString("Escalón aditivo fijo (ppb)", $fTickBold, $bSub, ($p2x + 4.5 * $step2), ($p2y + 13), $sfCenter)

for ($i = 0; $i -lt 6; $i++) {
    $cx = $p2x + ($i + 0.5) * $step2
    $v1 = [float]$rec999[$i]
    $v2 = [float]$rec99[$i]

    $h1 = $v1 * $p2h
    $h2 = $v2 * $p2h
    $g.FillRectangle($b999, [float]($cx - $bw - 3), [float]($p2y + $p2h - $h1), $bw, [float]$h1)
    $g.FillRectangle($b99,  [float]($cx + 3),       [float]($p2y + $p2h - $h2), $bw, [float]$h2)

    $s1 = $v1.ToString("0.00", [System.Globalization.CultureInfo]::InvariantCulture)
    $s2 = $v2.ToString("0.00", [System.Globalization.CultureInfo]::InvariantCulture)
    $g.DrawString($s1, $fVal, $b999, ($cx - $bw/2 - 3), ($p2y + $p2h - $h1 - 13), $sfCenter)
    $g.DrawString($s2, $fVal, $b99,  ($cx + $bw/2 + 3), ($p2y + $p2h - $h2 - 13), $sfCenter)

    $g.DrawString($lblsTam[$i], $fTickBold, $bTxt, $cx, ($p2y + $p2h + 24), $sfCenter)
}
$g.DrawString("Magnitud de la anomalía inyectada en 1 estación (E1)", $fAxisLbl, $bTxt, ($p2x + $p2w/2), ($p2y + $p2h + 68), $sfCenter)

# Leyenda inferior clara
$ly = 868
$itemsLeg = @(
    @{ c = $cVerde;    t = "Panel A: Recall con δ = 100%" },
    @{ c = $cAzul;     t = "Panel A: Recall con δ = 50%   |   Panel B: Recall en umbral p99 (4.7 días FA/año en banco)" },
    @{ c = $cNaranja;  t = "Panel A: Recall con δ = 20%" },
    @{ c = $cAzulClar; t = "Panel B: Recall en umbral p99.9 (0.7 días FA/año en banco)" }
)
$lx = 140
foreach ($it in $itemsLeg) {
    $bb = New-Object System.Drawing.SolidBrush($it.c)
    $g.FillRectangle($bb, $lx, $ly - 7, 20, 14)
    $g.DrawString($it.t, $fLegend, $bTxt, $lx + 26, $ly, $sfLeft)
    $sz = $g.MeasureString($it.t, $fLegend)
    $lx += [int]$sz.Width + 52
    $bb.Dispose()
}

Save-Both $cv.bmp "fig1_punto_operacion.png"

# ==============================================================================
# GRÁFICA 2 (LÁMINA 8): 1 estación atacada en p99
# SOLO: Ensamble vecinal con filtro (final), PARAAD-SA y experimentos TINTO (AE y Temporal-7d)
# ==============================================================================
$cv = Init-Canvas 1850 930
$g = $cv.g

$g.DrawString("Sensibilidad (Recall) con 1 estación atacada en el umbral p99 (~3.6 días/año nominales de FA)", $fTitle, $bTxt, 925, 32, $sfCenter)
$g.DrawString("Comparación directa: Ensamble vecinal con filtro (final) vs. PARAAD-SA vs. pilotos TINTO (Autoencoder y Temporal 7 días)", $fSubtitle, $bSub, 925, 64, $sfCenter)

# Valores oficiales en p99 para 1 estación:
# Proporcionales (d20, d50, d100) + Despliegue (d50, d100)
# Escalón fijo (+10, +20, +40 ppb)
# TINTO AE (7154 días 2022, aumentos): d20=0.036, d50=0.121, d100=0.355 | +10=0.016, +20=0.018, +40=0.017
# TINTO Temporal-7d (175 días 2022, aumentos): d20=0.063, d50=0.171, d100=0.514 | +10=0.057, +20=0.154, +40=1.000
$tintoAE_prop   = @(0.0361, 0.1209, 0.3551)
$tintoTemp_prop = @(0.0629, 0.1714, 0.5143)
$tintoAE_ppb    = @(0.0158, 0.0183, 0.0166)
$tintoTemp_ppb  = @(0.0571, 0.1543, 1.0000)

# Panel A: Anomalías proporcionales (δ = 20%, 50%, 100%) + Despliegue (ago-sep 2026)
$p1x = 105; $p1y = 180; $p1w = 810; $p1h = 525
Draw-YGridAndAxis $g $p1x $p1y $p1w $p1h "Sensibilidad (Recall) [escala 0.0 a 1.0]"
$g.DrawString("A. Anomalías proporcionales (δ%) y validación en despliegue (p99)", $fPanel, $bTxt, ($p1x + $p1w/2), ($p1y - 62), $sfCenter)

$bHdr = New-Object System.Drawing.SolidBrush($cHeaderBg)
$pHdr = New-Object System.Drawing.Pen($cBorde, 1.2)
$g.FillRectangle($bHdr, [float]$p1x, [float]($p1y - 44), [float]$p1w, 26.0)
$g.DrawRectangle($pHdr, [float]$p1x, [float]($p1y - 44), [float]$p1w, 26.0)

$gStepA = $p1w / 4.0
$pDash = New-Object System.Drawing.Pen($cBorde, 1.4)
$pDash.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
$g.DrawLine($pDash, ($p1x + 3 * $gStepA), ($p1y - 44), ($p1x + 3 * $gStepA), ($p1y + $p1h))
$g.DrawString("Banco de pruebas (2024–2026) / Exploración TINTO (2022)", $fTickBold, $bSub, ($p1x + 1.5 * $gStepA), ($p1y - 31), $sfCenter)
$g.DrawString("Despliegue (ago–sep 26)", $fTickBold, $bSub, ($p1x + 3.5 * $gStepA), ($p1y - 31), $sfCenter)

$lblsProp = @("δ = 20%", "δ = 50%", "δ = 100%", "Despliegue`n(δ=50% | 100%)")
$colsDet = @($cAzul, $cVerde, $cMorado, $cNaranja)
$barW = 30.0

for ($gi = 0; $gi -lt 4; $gi++) {
    $cx = $p1x + ($gi + 0.5) * $gStepA
    if ($gi -lt 3) {
        $vals = @(
            [float]$datos.g2_banco."Ens-Vb-X0.2596".recall[$gi],
            [float]$datos.g2_banco."PARAAD".recall[$gi],
            [float]$tintoAE_prop[$gi],
            [float]$tintoTemp_prop[$gi]
        )
        for ($di = 0; $di -lt 4; $di++) {
            $v = $vals[$di]
            $bh = $v * $p1h
            $bx = $cx + ($di - 2.0) * ($barW + 4.0) + 2.0
            $by = $p1y + $p1h - $bh
            $br = New-Object System.Drawing.SolidBrush($colsDet[$di])
            $g.FillRectangle($br, [float]$bx, [float]$by, $barW, [float]$bh)
            $sVal = $v.ToString("0.00", [System.Globalization.CultureInfo]::InvariantCulture)
            $g.DrawString($sVal, $fVal, $br, ($bx + $barW/2), ($by - 13), $sfCenter)
            $br.Dispose()
        }
    } else {
        $v50  = [float]$datos.g2_desp.recall[1]
        $v100 = [float]$datos.g2_desp.recall[2]
        $bh50  = $v50 * $p1h
        $bh100 = $v100 * $p1h
        $br1 = New-Object System.Drawing.SolidBrush($cAzul)
        $br2 = New-Object System.Drawing.SolidBrush($cAzulClar)
        $g.FillRectangle($br1, [float]($cx - 34), [float]($p1y + $p1h - $bh50),  30.0, [float]$bh50)
        $g.FillRectangle($br2, [float]($cx + 4),  [float]($p1y + $p1h - $bh100), 30.0, [float]$bh100)
        $g.DrawString($v50.ToString("0.00", [System.Globalization.CultureInfo]::InvariantCulture),  $fVal, $br1, ($cx - 19), ($p1y + $p1h - $bh50 - 13), $sfCenter)
        $g.DrawString($v100.ToString("0.00", [System.Globalization.CultureInfo]::InvariantCulture), $fVal, $br2, ($cx + 19), ($p1y + $p1h - $bh100 - 13), $sfCenter)
        $br1.Dispose(); $br2.Dispose()
    }
    $g.DrawString($lblsProp[$gi], $fTickBold, $bTxt, $cx, ($p1y + $p1h + 26), $sfCenter)
}
$g.DrawString("Magnitud de anomalía proporcional (δ%)", $fAxisLbl, $bTxt, ($p1x + $p1w/2), ($p1y + $p1h + 70), $sfCenter)

# Panel B: Escalón aditivo fijo (+10 ppb, +20 ppb, +40 ppb)
$p2x = 1015; $p2y = 180; $p2w = 760; $p2h = 525
Draw-YGridAndAxis $g $p2x $p2y $p2w $p2h "Sensibilidad (Recall) [escala 0.0 a 1.0]"
$g.DrawString("B. Anomalías de escalón aditivo fijo (+10, +20 y +40 ppb en p99)", $fPanel, $bTxt, ($p2x + $p2w/2), ($p2y - 62), $sfCenter)

$g.FillRectangle($bHdr, [float]$p2x, [float]($p2y - 44), [float]$p2w, 26.0)
$g.DrawRectangle($pHdr, [float]$p2x, [float]($p2y - 44), [float]$p2w, 26.0)
$g.DrawString("Escalón aditivo fijo en ppb (Banco 2024–2026 / Exploración TINTO 2022)", $fTickBold, $bSub, ($p2x + $p2w/2), ($p2y - 31), $sfCenter)
$bHdr.Dispose(); $pHdr.Dispose(); $pDash.Dispose()

$lblsPpb = @("+10 ppb", "+20 ppb", "+40 ppb")
$gStepB = $p2w / 3.0
$barWB = 34.0

for ($gi = 0; $gi -lt 3; $gi++) {
    $cx = $p2x + ($gi + 0.5) * $gStepB
    $vals = @(
        [float]$datos.g2_banco."Ens-Vb-X0.2596".recall[$gi + 3],
        [float]$datos.g2_banco."PARAAD".recall[$gi + 3],
        [float]$tintoAE_ppb[$gi],
        [float]$tintoTemp_ppb[$gi]
    )
    for ($di = 0; $di -lt 4; $di++) {
        $v = $vals[$di]
        $bh = $v * $p2h
        $bx = $cx + ($di - 2.0) * ($barWB + 5.0) + 2.5
        $by = $p2y + $p2h - $bh
        $br = New-Object System.Drawing.SolidBrush($colsDet[$di])
        $g.FillRectangle($br, [float]$bx, [float]$by, $barWB, [float]$bh)
        $sVal = $v.ToString("0.00", [System.Globalization.CultureInfo]::InvariantCulture)
        $dyLbl = if ($v -ge 0.98) { -12 } else { -13 }
        $g.DrawString($sVal, $fVal, $br, ($bx + $barWB/2), ($by + $dyLbl), $sfCenter)
        $br.Dispose()
    }
    $g.DrawString($lblsPpb[$gi], $fTickBold, $bTxt, $cx, ($p2y + $p2h + 26), $sfCenter)
}
$g.DrawString("Magnitud de anomalía aditiva fija (ppb)", $fAxisLbl, $bTxt, ($p2x + $p2w/2), ($p2y + $p2h + 70), $sfCenter)

# Leyenda inferior de los 4 modelos (nuestro mejor modelo, PARAAD y los 2 pilotos de TINTO)
$ly = 862
$leg2 = @(
    @{ c = $cAzul;    t = "Ensamble vecinal con filtro (final)" },
    @{ c = $cVerde;   t = "PARAAD-SA" },
    @{ c = $cMorado;  t = "TINTO Autoencoder (1 día, 2022)" },
    @{ c = $cNaranja; t = "TINTO Temporal 7 días (CNN, 2022)" }
)
$lx = 165
foreach ($it in $leg2) {
    $bb = New-Object System.Drawing.SolidBrush($it.c)
    $g.FillRectangle($bb, $lx, $ly - 8, 22, 16)
    $g.DrawString($it.t, $fLegend, $bTxt, $lx + 28, $ly, $sfLeft)
    $sz = $g.MeasureString($it.t, $fLegend)
    $lx += [int]$sz.Width + 55
    $bb.Dispose()
}
$g.DrawString("Nota: TINTO se muestra como referencia exploratoria en 2022 (estación-día sin contexto espacial de vecinas). En +40 ppb, añadir 7 días de historia a TINTO eleva el Recall a 1.00.", $fNote, $bSub, 925, 898, $sfCenter)

Save-Both $cv.bmp "fig2_una_estacion_p99.png"

# ==============================================================================
# GRÁFICA 3 (LÁMINA 9): Ataque coordinado a vecinas (0, 1, 2, 3, 4) en p99
# SOLO líneas sólidas: Ensamble vecinal con filtro (final), PARAAD-SA y referencia TINTO
# Panel A: Sensibilidad (Recall) en δ = 50% | Panel B: Sensibilidad (Recall) en +20 ppb
# ==============================================================================
$cv = Init-Canvas 1850 920
$g = $cv.g

$g.DrawString("Robustez ante ataque coordinado a estaciones vecinas (umbral p99)", $fTitle, $bTxt, 925, 32, $sfCenter)
$g.DrawString("Sensibilidad (Recall en la estación atacada) según el número de vecinas comprometidas (escala uniforme de 0 a 4)", $fSubtitle, $bSub, 925, 64, $sfCenter)

$panelsG3 = @(
    @{ tam = "d50"; title = "A. Anomalía proporcional (δ = 50%)";       tintoAE = 0.1209; tintoT7 = 0.1714 },
    @{ tam = "a20"; title = "B. Escalón aditivo fijo (+20 ppb)";        tintoAE = 0.0183; tintoT7 = 0.1543 }
)

for ($pi = 0; $pi -lt 2; $pi++) {
    $px = if ($pi -eq 0) { 115 } else { 995 }
    $py = 155; $pw = 760; $ph = 550
    $cfg = $panelsG3[$pi]

    Draw-YGridAndAxis $g $px $py $pw $ph "Sensibilidad (Recall en estación atacada) [0.0 a 1.0]"
    $g.DrawString($cfg.title, $fPanel, $bTxt, ($px + $pw/2), ($py - 28), $sfCenter)

    # Eje X numérico estricto de 1 en 1: 0, 1, 2, 3, 4
    $xPad = 65.0
    $xSpan = $pw - 2 * $xPad
    for ($xv = 0; $xv -le 4; $xv++) {
        $xx = $px + $xPad + ($xv / 4.0) * $xSpan
        $g.DrawLine($pVGrid, $xx, $py, $xx, $py + $ph)
        $g.DrawString("$xv vecinas", $fTickBold, $bTxt, $xx, ($py + $ph + 24), $sfCenter)
    }
    $g.DrawString("Número de estaciones vecinas comprometidas simultáneamente (0 a 4)", $fAxisLbl, $bTxt, ($px + $pw/2), ($py + $ph + 66), $sfCenter)

    $xCoords = @(0, 1, 2, 4) | ForEach-Object { $px + $xPad + ($_ / 4.0) * $xSpan }
    $tamKey = $cfg.tam
    $vVb = $datos.g3.$tamKey."Ens-Vb-X0.2596".recall
    $vPa = $datos.g3.$tamKey."PARAAD".recall
    $vT7 = @($cfg.tintoT7, $cfg.tintoT7, $cfg.tintoT7, $cfg.tintoT7)

    # Todas como líneas sólidas claras
    if ($pi -eq 0) {
        Draw-SeriesCustom $g $xCoords $vVb $py $ph $cAzul    $false @(-16, -16, -16, -16)
        Draw-SeriesCustom $g $xCoords $vPa $py $ph $cVerde   $false @(-16, -16,  18, -16)
        Draw-SeriesCustom $g $xCoords $vT7 $py $ph $cNaranja $false @(-16, -16, -16, -16)
    } else {
        Draw-SeriesCustom $g $xCoords $vVb $py $ph $cAzul    $false @(-16, -16, -16, -16)
        Draw-SeriesCustom $g $xCoords $vPa $py $ph $cVerde   $false @( 18,  18, -16, -16)
        Draw-SeriesCustom $g $xCoords $vT7 $py $ph $cNaranja $false @(-16, -16, -16, -16)
    }
}

$ly = 852
$leg3 = @(
    @{ c = $cAzul;    t = "Ensamble vecinal con filtro (final) — usa vecinas y filtra hasta 2 sospechosas (4.7 d/año FA)" },
    @{ c = $cVerde;   t = "PARAAD-SA — no usa vecinas (9.6 d/año FA)" },
    @{ c = $cNaranja; t = "TINTO Temporal 7 días (2022) — no usa vecinas" }
)
$lx = 115
foreach ($it in $leg3) {
    $bb = New-Object System.Drawing.SolidBrush($it.c)
    $g.FillRectangle($bb, $lx, $ly - 8, 22, 16)
    $g.DrawString($it.t, $fLegend, $bTxt, $lx + 28, $ly, $sfLeft)
    $sz = $g.MeasureString($it.t, $fLegend)
    $lx += [int]$sz.Width + 45
    $bb.Dispose()
}
$g.DrawString("Nota: Con 0 y 1 vecina comprometida, el Ensamble vecinal con filtro supera ampliamente a los modelos sin vecinas; al comprometer las 4 vecinas pierde su referencia limpia.", $fNote, $bSub, 925, 892, $sfCenter)

Save-Both $cv.bmp "fig3_ataque_coordinado_p99.png"
