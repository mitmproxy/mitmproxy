$tool = $args[0]
if (Get-Command wt -ErrorAction SilentlyContinue) {
	Start-Process wt -ArgumentList "powershell.exe","-Command","& '$PSScriptRoot\bin\$tool.exe'"
} else { 
	Start-Process powershell -ArgumentList "-Command","& '$PSScriptRoot\bin\$tool.exe'"
}
