$doc_path = "C:\Users\Administrator\.hermes\智能看盘\.hermes\desktop-attachments\盯盘交易-2.doc"
$output_path = "C:\Users\Administrator\.hermes\智能看盘\盯盘交易-2.txt"

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($doc_path)
    $text = @()
    foreach ($para in $doc.Paragraphs) {
        $t = $para.Range.Text.Trim()
        if ($t) { $text += $t }
    }
    # Also extract tables
    foreach ($table in $doc.Tables) {
        foreach ($row in $table.Rows) {
            $rowText = @()
            foreach ($cell in $row.Cells) {
                $cellText = $cell.Range.Text.Trim()
                if ($cellText.Length -gt 2) {
                    $rowText += $cellText.Substring(0, $cellText.Length-2)
                }
            }
            $text += ($rowText -join "`t")
        }
    }
    $result = $text -join "`n"
    $doc.Close($false)
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    $result | Out-File -FilePath $output_path -Encoding UTF8
    Write-Host "SUCCESS: $($result.Length) chars extracted"
} catch {
    Write-Host "ERROR: $_"
}
