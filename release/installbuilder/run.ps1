$tool = $args[0]
if ((Get-Command wt -ErrorAction SilentlyContinue) -and ((Get-ItemProperty -LiteralPath 'HKCU:\Console\%%Startup' -Name 'DelegationConsole' -ErrorAction SilentlyContinue).DelegationConsole -ne '{B23D10C0-E52E-411E-9D5B-C09FDF709C7D}')) {
	Start-Process wt -ArgumentList "powershell.exe","-Command","& '$PSScriptRoot\bin\$tool.exe'"
} else { 
	Start-Process powershell -ArgumentList "-Command","& '$PSScriptRoot\bin\$tool.exe'"
}
