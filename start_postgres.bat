@echo off
echo PostgreSQL 18 Baslatiliyor...
"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D "C:\Program Files\PostgreSQL\18\data" -l "%~dp0postgres.log" start
echo PostgreSQL Durumu:
"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D "C:\Program Files\PostgreSQL\18\data" status
pause
