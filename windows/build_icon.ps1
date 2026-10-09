# Convert the existing upstream face asset to a multi-resolution Windows icon.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$Root = Split-Path $PSScriptRoot -Parent
$Source = Join-Path $Root 'docs/face-ok.png'
$Destination = Join-Path $PSScriptRoot 'assets/chip.ico'
$Sizes = @(16, 24, 32, 48, 64, 128, 256)
$Frames = [Collections.Generic.List[byte[]]]::new()
$Image = [Drawing.Image]::FromFile($Source)
try {
    foreach ($Size in $Sizes) {
        $Bitmap = [Drawing.Bitmap]::new($Size, $Size, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $Graphics = [Drawing.Graphics]::FromImage($Bitmap)
        $Stream = [IO.MemoryStream]::new()
        try {
            $Graphics.Clear([Drawing.Color]::Transparent)
            $Graphics.CompositingMode = [Drawing.Drawing2D.CompositingMode]::SourceCopy
            $Graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $Graphics.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $Graphics.DrawImage($Image, [Drawing.Rectangle]::new(0, 0, $Size, $Size))
            $Bitmap.Save($Stream, [Drawing.Imaging.ImageFormat]::Png)
            $Frames.Add($Stream.ToArray())
        } finally {
            $Stream.Dispose(); $Graphics.Dispose(); $Bitmap.Dispose()
        }
    }
} finally { $Image.Dispose() }
[IO.Directory]::CreateDirectory((Split-Path $Destination)) | Out-Null
$File = [IO.File]::Create($Destination)
$Writer = [IO.BinaryWriter]::new($File)
try {
    $Writer.Write([uint16]0); $Writer.Write([uint16]1); $Writer.Write([uint16]$Sizes.Count)
    $Offset = 6 + 16 * $Sizes.Count
    for ($i=0; $i -lt $Sizes.Count; $i++) {
        $Dim = if ($Sizes[$i] -eq 256) { 0 } else { $Sizes[$i] }
        $Writer.Write([byte]$Dim); $Writer.Write([byte]$Dim)
        $Writer.Write([byte]0); $Writer.Write([byte]0)
        $Writer.Write([uint16]1); $Writer.Write([uint16]32)
        $Writer.Write([uint32]$Frames[$i].Length); $Writer.Write([uint32]$Offset)
        $Offset += $Frames[$i].Length
    }
    foreach ($Frame in $Frames) { $Writer.Write($Frame) }
} finally { $Writer.Dispose(); $File.Dispose() }
Write-Host "Generated $Destination from docs/face-ok.png"
