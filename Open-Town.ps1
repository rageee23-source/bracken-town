param([switch]$Headless)
$ErrorActionPreference='Stop'
$addr='http://127.0.0.1:8798'
try { $town=Invoke-RestMethod "$addr/api/town" -TimeoutSec 2 } catch {$town=$null}
if (!$town) {
 if (!$env:OPENAI_API_KEY) {
   $source=Join-Path $env:USERPROFILE 'dev\automaton-sandbox\proxy.env'
   if(Test-Path $source){$line=Get-Content -LiteralPath $source | Where-Object {$_ -match '^OPENAI_API_KEY='} | Select-Object -First 1; if($line){$env:OPENAI_API_KEY=$line.Substring(15).Trim().Trim('"').Trim("'")}}
 }
 $script=Join-Path $PSScriptRoot 'town.py'
 Start-Process (Get-Command pythonw.exe).Source -ArgumentList ('"'+$script+'"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
 for($i=0;$i -lt 30;$i++){Start-Sleep -Milliseconds 300;try{$town=Invoke-RestMethod "$addr/api/town" -TimeoutSec 2;break}catch{}}
 if(!$town){throw 'Town server did not start.'}
}
if (!$Headless) {Start-Process $addr}
