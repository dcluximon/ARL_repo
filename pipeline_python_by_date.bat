@ECHO OFF

IF "%1"=="" GOTO Continue

set "query_day=%1"

set APPDIR="*INPUT DIR*/ARL_repo"
set LOGFILE="*INPUT DIR*/ARL_repo/outputs/logs/%query_day%_logfile.txt"

for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "datestamp=%YYYY%-%MM%-%DD%" & set "timestamp=%HH%:%Min%:%Sec%"
ECHO %datestamp% > %LOGFILE% 
ECHO. >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO %timestamp% : Daily CBCT Analysis Pipeline for Treatments on %query_day% >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO. >> %LOGFILE% 

cd %APPDIR%

CALL conda.bat activate dicom

for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%HH%:%Min%:%Sec%"
ECHO. >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO %timestamp% : [01] Querying Daily Treatment List... >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO. >> %LOGFILE% 
ECHO %timestamp% : [01] Querying Daily Treatment List...
python a01_find_daily_tx_list.py %query_day% >> %LOGFILE% 
::01-find_daily_tx_list.exe %query_day% >> %LOGFILE%  

for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%HH%:%Min%:%Sec%"
ECHO. >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO %timestamp% : [02] Querying Daily CT Acquisition List... >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO. >> %LOGFILE% 
ECHO %timestamp% : [02] Querying Daily CT Acquisition List...
python a02_find_daily_ct_list.py %query_day% >> %LOGFILE% 
::02-find_daily_ct_list.exe %query_day% >> %LOGFILE% 

for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%HH%:%Min%:%Sec%"
ECHO. >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO %timestamp% : [03] Cross Referencing Tx and CT Lists... >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO. >> %LOGFILE% 
ECHO %timestamp% : [03] Cross Referencing Tx and CT Lists...
python a03_cross_reference_tx_ct_lists.py %query_day% >> %LOGFILE% 
::03-cross_reference_tx_ct_lists.exe >> %LOGFILE% 

for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%HH%:%Min%:%Sec%"
ECHO. >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO %timestamp% : [04] Retrieving Daily Registrations... >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO. >> %LOGFILE% 
ECHO %timestamp% : [04] Retrieving Daily Registrations...
python a04_move_daily_tx_ct_regs.py %query_day% >> %LOGFILE% 
::04-move_daily_tx_ct_regs.exe %query_day% >> %LOGFILE% 

for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%HH%:%Min%:%Sec%"
ECHO. >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO %timestamp% : [05] Retrieving Relevant RTPlans... >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO. >> %LOGFILE% 
ECHO %timestamp% : [05] Retrieving Relevant RTPlans...
python a05_inspect_daily_regs.py %query_day% >> %LOGFILE% 
::05-inspect_daily_regs.exe %query_day% >> %LOGFILE% 

for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%HH%:%Min%:%Sec%"
ECHO. >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO %timestamp% : [06] Retrieving Relevant CT Images... >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO. >> %LOGFILE% 
ECHO %timestamp% : [06] Retrieving Relevant CT Images...
python a06_inspect_daily_rtplans.py %query_day% >> %LOGFILE% 
::06-inspect_daily_rtplans.exe %query_day% >> %LOGFILE% 

CALL conda.bat activate tensor6

for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%HH%:%Min%:%Sec%"
ECHO. >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO %timestamp% : [07] Running Image Analysis...  >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO. >> %LOGFILE% 
ECHO %timestamp% : [07] Running Image Analysis...
python a07_ARL.py %query_day% >> %LOGFILE% 
::07-ARL.exe >> %LOGFILE% 

CALL conda.bat activate dicom

for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%HH%:%Min%:%Sec%"
ECHO. >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO %timestamp% : [08] Generating Daily Report...  >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO. >> %LOGFILE% 
ECHO %timestamp% : [08] Generating Daily Report...
python a08_send_daily_report.py %query_day% >> %LOGFILE% 
::08-send_daily_report.exe %query_day% >> %LOGFILE% 

for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%HH%:%Min%:%Sec%"
ECHO. >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO %timestamp% : [09] Cleaning Up DICOM Files and Archiving Results... >> %LOGFILE% 
ECHO ------------------------------------------------------------------------ >> %LOGFILE% 
ECHO. >> %LOGFILE% 
ECHO %timestamp% : [09] Cleaning Up DICOM Files and Archiving Results...
:: PAUSE
python a09_clean_daily_files.py %query_day%
::09-clean_daily_files.exe %query_day%

:Continue
ECHO PIPELINE_BY_DATE Batch file execution requires the date as a command line argument in ISO FORMAT: YYYY-MM-DD