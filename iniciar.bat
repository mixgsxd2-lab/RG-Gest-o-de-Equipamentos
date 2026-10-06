@echo off
chcp 65001 >nul
title RG Manutencao - Hospital Rio Grande
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale o Python 3.10+ em https://www.python.org/downloads/
  echo Marque a opcao "Add python.exe to PATH" durante a instalacao.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente virtual...
  python -m venv .venv
)
echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 ( echo Falha ao instalar dependencias. & pause & exit /b 1 )

set PORT=5000
echo.
echo ===============================================
echo   RG Manutencao rodando em http://localhost:%PORT%
echo   Login de teste: admin / 123456
echo   Para encerrar: feche esta janela ou Ctrl+C
echo ===============================================
start "" http://localhost:%PORT%
".venv\Scripts\python.exe" run.py
pause
