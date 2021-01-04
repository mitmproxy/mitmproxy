if (Get-Command wt -ErrorAction SilentlyContinue) { 
	Start-Process wt -ArgumentList "powershell.exe","-NoExit","-Command",$args[0]
} else { 
	Start-Process powershell -ArgumentList "-NoExit","-Command",$args[0]
}
