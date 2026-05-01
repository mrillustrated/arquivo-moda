
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Application]::EnableVisualStyles()

$ErrorActionPreference = "Stop"

function Slugify([string]$text) {
    if ([string]::IsNullOrWhiteSpace($text)) { return "imagens" }
    $normalized = $text.Normalize([Text.NormalizationForm]::FormD)
    $sb = New-Object System.Text.StringBuilder
    foreach ($ch in $normalized.ToCharArray()) {
        $cat = [Globalization.CharUnicodeInfo]::GetUnicodeCategory($ch)
        if ($cat -ne [Globalization.UnicodeCategory]::NonSpacingMark) {
            [void]$sb.Append($ch)
        }
    }
    $clean = $sb.ToString() -replace '[^a-zA-Z0-9]+','_' -replace '^_+|_+$',''
    if ([string]::IsNullOrWhiteSpace($clean)) { return "imagens" }
    return $clean.ToLower()
}

function Remove-ResizeSuffix([string]$path) {
    return [regex]::Replace($path, '-\d+x\d+(?=\.[A-Za-z0-9]+$)', '')
}

function Get-PageHtml([string]$url) {
    $resp = Invoke-WebRequest -Uri $url -UseBasicParsing
    return $resp.Content
}

function Resolve-Url([string]$baseUrl, [string]$value) {
    try {
        if ([string]::IsNullOrWhiteSpace($value)) { return $null }
        if ($value.StartsWith("data:")) { return $null }
        $base = [Uri]$baseUrl
        $uri = [Uri]::new($base, $value)
        return $uri.AbsoluteUri
    } catch {
        return $null
    }
}

function Looks-LikeImage([string]$url) {
    if ([string]::IsNullOrWhiteSpace($url)) { return $false }
    $u = $url.ToLower()
    return ($u -match '\.(jpg|jpeg|png|webp|gif|bmp|avif|svg)(\?|#|$)') -or
           $u.Contains('format=jpg') -or
           $u.Contains('format=png') -or
           $u.Contains('/wp-content/uploads/') -or
           $u.Contains('image')
}

function Extract-ImageUrls([string]$baseUrl, [string]$html, [bool]$sameDomain, [bool]$dedupeResized) {
    $results = New-Object System.Collections.Generic.List[string]

    $patterns = @(
        '(?i)(?:src|data-src|data-lazy-src|data-original|data-image|href|content)\s*=\s*["'']([^"'']+)["'']',
        '(?i)(?:srcset|data-srcset)\s*=\s*["'']([^"'']+)["'']',
        '(?i)https?:\/\/[^"''\s)]+',
        '(?i)["''](\/[^"'']+\.(?:jpg|jpeg|png|webp|gif|bmp|avif|svg)[^"'']*)["'']'
    )

    foreach ($pattern in $patterns) {
        $matches = [regex]::Matches($html, $pattern)
        foreach ($m in $matches) {
            $value = $m.Groups[1].Value
            if ([string]::IsNullOrWhiteSpace($value)) { $value = $m.Value }
            if ($value -match ',') {
                $parts = $value -split ','
                foreach ($part in $parts) {
                    $candidate = ($part.Trim() -split '\s+')[0]
                    $abs = Resolve-Url $baseUrl $candidate
                    if ($abs -and (Looks-LikeImage $abs)) { $results.Add($abs) }
                }
            } else {
                $candidate = $value.Trim()
                $abs = Resolve-Url $baseUrl $candidate
                if ($abs -and (Looks-LikeImage $abs)) { $results.Add($abs) }
            }
        }
    }

    $styleMatches = [regex]::Matches($html, '(?i)url\((.*?)\)')
    foreach ($m in $styleMatches) {
        $candidate = $m.Groups[1].Value.Trim("'`" ")
        $abs = Resolve-Url $baseUrl $candidate
        if ($abs -and (Looks-LikeImage $abs)) { $results.Add($abs) }
    }

    $unique = New-Object System.Collections.Generic.List[string]
    $seen = @{}

    $baseHost = $null
    try { $baseHost = ([Uri]$baseUrl).Host } catch {}

    foreach ($u in $results) {
        try {
            $uri = [Uri]$u
            if ($sameDomain -and $baseHost -and $uri.Host -ne $baseHost) { continue }
            $key = $u
            if ($dedupeResized) {
                $key = $uri.Host + (Remove-ResizeSuffix $uri.AbsolutePath)
            }
            if (-not $seen.ContainsKey($key)) {
                $seen[$key] = $true
                $unique.Add($u)
            }
        } catch {}
    }

    return $unique
}

function Get-FileNameFromUrl([string]$url, [int]$index) {
    try {
        $uri = [Uri]$url
        $name = [IO.Path]::GetFileName($uri.AbsolutePath)
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            return ($name -replace '[\\/:*?"<>|]', '_')
        }
    } catch {}
    return ('imagem_{0:D4}.jpg' -f ($index + 1))
}

function Get-UniquePath([string]$Path) {
    if (-not (Test-Path $Path)) { return $Path }
    $dir = Split-Path $Path
    $name = [System.IO.Path]::GetFileNameWithoutExtension($Path)
    $ext = [System.IO.Path]::GetExtension($Path)
    $i = 2
    do {
        $candidate = Join-Path $dir ($name + "_" + $i + $ext)
        $i++
    } while (Test-Path $candidate)
    return $candidate
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Extrator de Imagens"
$form.Size = New-Object System.Drawing.Size(1180, 760)
$form.StartPosition = "CenterScreen"
$form.BackColor = [System.Drawing.Color]::FromArgb(18,22,30)
$form.ForeColor = [System.Drawing.Color]::White

$font = New-Object System.Drawing.Font("Segoe UI", 10)
$form.Font = $font

$lblUrl = New-Object System.Windows.Forms.Label
$lblUrl.Text = "Link da página"
$lblUrl.Location = New-Object System.Drawing.Point(20, 20)
$lblUrl.Size = New-Object System.Drawing.Size(150, 24)
$form.Controls.Add($lblUrl)

$txtUrl = New-Object System.Windows.Forms.TextBox
$txtUrl.Location = New-Object System.Drawing.Point(20, 45)
$txtUrl.Size = New-Object System.Drawing.Size(820, 30)
$txtUrl.Text = "https://spfw.com.br/desfile/apartamento03/"
$form.Controls.Add($txtUrl)

$btnExtract = New-Object System.Windows.Forms.Button
$btnExtract.Text = "Extrair imagens"
$btnExtract.Location = New-Object System.Drawing.Point(860, 43)
$btnExtract.Size = New-Object System.Drawing.Size(130, 34)
$form.Controls.Add($btnExtract)

$btnSelectAll = New-Object System.Windows.Forms.Button
$btnSelectAll.Text = "Selecionar tudo"
$btnSelectAll.Location = New-Object System.Drawing.Point(1000, 43)
$btnSelectAll.Size = New-Object System.Drawing.Size(130, 34)
$form.Controls.Add($btnSelectAll)

$chkSameDomain = New-Object System.Windows.Forms.CheckBox
$chkSameDomain.Text = "Mesmo domínio"
$chkSameDomain.Location = New-Object System.Drawing.Point(20, 90)
$chkSameDomain.Size = New-Object System.Drawing.Size(150, 24)
$chkSameDomain.Checked = $true
$form.Controls.Add($chkSameDomain)

$chkDedupe = New-Object System.Windows.Forms.CheckBox
$chkDedupe.Text = "Remover redimensionadas"
$chkDedupe.Location = New-Object System.Drawing.Point(180, 90)
$chkDedupe.Size = New-Object System.Drawing.Size(220, 24)
$chkDedupe.Checked = $true
$form.Controls.Add($chkDedupe)

$lblZip = New-Object System.Windows.Forms.Label
$lblZip.Text = "Nome do ZIP"
$lblZip.Location = New-Object System.Drawing.Point(420, 90)
$lblZip.Size = New-Object System.Drawing.Size(100, 24)
$form.Controls.Add($lblZip)

$txtZip = New-Object System.Windows.Forms.TextBox
$txtZip.Location = New-Object System.Drawing.Point(520, 88)
$txtZip.Size = New-Object System.Drawing.Size(320, 30)
$txtZip.Text = "apartamento03"
$form.Controls.Add($txtZip)

$btnDownload = New-Object System.Windows.Forms.Button
$btnDownload.Text = "Baixar + ZIP"
$btnDownload.Location = New-Object System.Drawing.Point(860, 86)
$btnDownload.Size = New-Object System.Drawing.Size(130, 34)
$form.Controls.Add($btnDownload)

$btnSaveList = New-Object System.Windows.Forms.Button
$btnSaveList.Text = "Salvar lista TXT"
$btnSaveList.Location = New-Object System.Drawing.Point(1000, 86)
$btnSaveList.Size = New-Object System.Drawing.Size(130, 34)
$form.Controls.Add($btnSaveList)

$list = New-Object System.Windows.Forms.CheckedListBox
$list.Location = New-Object System.Drawing.Point(20, 130)
$list.Size = New-Object System.Drawing.Size(1110, 470)
$list.CheckOnClick = $true
$list.HorizontalScrollbar = $true
$form.Controls.Add($list)

$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object System.Drawing.Point(20, 615)
$progress.Size = New-Object System.Drawing.Size(1110, 24)
$form.Controls.Add($progress)

$log = New-Object System.Windows.Forms.TextBox
$log.Location = New-Object System.Drawing.Point(20, 650)
$log.Size = New-Object System.Drawing.Size(1110, 60)
$log.Multiline = $true
$log.ScrollBars = "Vertical"
$log.ReadOnly = $true
$form.Controls.Add($log)

function Write-Log([string]$msg) {
    $time = Get-Date -Format "HH:mm:ss"
    $log.AppendText("[$time] $msg`r`n")
}

$script:CurrentUrls = @()

$btnExtract.Add_Click({
    try {
        $url = $txtUrl.Text.Trim()
        if ([string]::IsNullOrWhiteSpace($url)) {
            [System.Windows.Forms.MessageBox]::Show("Cole um link primeiro.")
            return
        }

        $list.Items.Clear()
        $progress.Value = 0
        Write-Log "Lendo página..."
        $html = Get-PageHtml $url
        $urls = Extract-ImageUrls $url $html $chkSameDomain.Checked $chkDedupe.Checked
        $script:CurrentUrls = @($urls)

        foreach ($u in $script:CurrentUrls) { [void]$list.Items.Add($u, $true) }

        if ([string]::IsNullOrWhiteSpace($txtZip.Text)) {
            try {
                $slug = Slugify(([Uri]$url).Segments[-1].Trim('/'))
                $txtZip.Text = $slug
            } catch {}
        }

        Write-Log ("Imagens encontradas: " + $script:CurrentUrls.Count)
        if ($script:CurrentUrls.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show("Nenhuma imagem encontrada. Tente outro link.")
        }
    } catch {
        Write-Log ("Erro: " + $_.Exception.Message)
        [System.Windows.Forms.MessageBox]::Show("Erro ao extrair: " + $_.Exception.Message)
    }
})

$btnSelectAll.Add_Click({
    for ($i = 0; $i -lt $list.Items.Count; $i++) {
        $list.SetItemChecked($i, $true)
    }
})

$btnSaveList.Add_Click({
    try {
        if ($list.Items.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show("Nada para salvar.")
            return
        }
        $dialog = New-Object System.Windows.Forms.SaveFileDialog
        $dialog.Filter = "TXT (*.txt)|*.txt"
        $dialog.FileName = ((Slugify $txtZip.Text) + "_links.txt")
        if ($dialog.ShowDialog() -eq "OK") {
            $selected = @()
            for ($i=0; $i -lt $list.Items.Count; $i++) {
                if ($list.GetItemChecked($i)) { $selected += [string]$list.Items[$i] }
            }
            if ($selected.Count -eq 0) { $selected = @($script:CurrentUrls) }
            Set-Content -Path $dialog.FileName -Value ($selected -join "`r`n") -Encoding UTF8
            Write-Log ("Lista salva: " + $dialog.FileName)
        }
    } catch {
        Write-Log ("Erro ao salvar lista: " + $_.Exception.Message)
    }
})

$btnDownload.Add_Click({
    try {
        if ($list.Items.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show("Extraia as imagens primeiro.")
            return
        }

        $selected = @()
        for ($i=0; $i -lt $list.Items.Count; $i++) {
            if ($list.GetItemChecked($i)) { $selected += [string]$list.Items[$i] }
        }
        if ($selected.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show("Selecione pelo menos uma imagem.")
            return
        }

        $desktop = [Environment]::GetFolderPath("Desktop")
        $root = Join-Path $desktop "downloads_imagens"
        New-Item -ItemType Directory -Force -Path $root | Out-Null

        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $slug = Slugify $txtZip.Text
        if ([string]::IsNullOrWhiteSpace($slug)) { $slug = "imagens" }

        $outDir = Join-Path $root ($slug + "_" + $stamp)
        New-Item -ItemType Directory -Force -Path $outDir | Out-Null

        $progress.Minimum = 0
        $progress.Maximum = $selected.Count
        $progress.Value = 0

        $ok = 0
        $fail = 0

        for ($i = 0; $i -lt $selected.Count; $i++) {
            $u = $selected[$i]
            try {
                $filename = Get-FileNameFromUrl $u $i
                $target = Get-UniquePath (Join-Path $outDir $filename)
                Invoke-WebRequest -Uri $u -OutFile $target -UseBasicParsing
                $ok++
                Write-Log ("OK: " + $filename)
            } catch {
                $fail++
                Write-Log ("ERRO: " + $u)
            }
            $progress.Value = [Math]::Min($i + 1, $progress.Maximum)
            [System.Windows.Forms.Application]::DoEvents()
        }

        $zipPath = Join-Path $root ($slug + ".zip")
        if (Test-Path $zipPath) { $zipPath = Join-Path $root ($slug + "_" + $stamp + ".zip") }
        Compress-Archive -Path (Join-Path $outDir "*") -DestinationPath $zipPath -Force

        Write-Log ("Concluído. Sucesso: $ok | Falhas: $fail")
        Write-Log ("ZIP: " + $zipPath)
        [System.Windows.Forms.MessageBox]::Show("Concluído.`n`nSucesso: $ok`nFalhas: $fail`nZIP: $zipPath")
    } catch {
        Write-Log ("Erro no download/zip: " + $_.Exception.Message)
        [System.Windows.Forms.MessageBox]::Show("Erro: " + $_.Exception.Message)
    }
})

Write-Log "Pronto. Cole um link e clique em Extrair imagens."

[void]$form.ShowDialog()
