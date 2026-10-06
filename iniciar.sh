#!/usr/bin/env bash
# Inicia o RG Manutenção localmente (Mac/Linux): ./iniciar.sh
set -e
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "Python não encontrado. Instale o Python 3.10+ (https://www.python.org/downloads/)"; exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "Criando ambiente virtual..."
  "$PY" -m venv .venv
fi
echo "Instalando dependências..."
.venv/bin/python -m pip install -q -r requirements.txt

export PORT="${PORT:-5000}"
echo
echo "==============================================="
echo "  RG Manutenção rodando em http://localhost:$PORT"
echo "  Login de teste: admin / 123456"
echo "  Para encerrar: Ctrl+C"
echo "==============================================="
(sleep 2; command -v xdg-open >/dev/null && xdg-open "http://localhost:$PORT" >/dev/null 2>&1 \
  || command -v open >/dev/null && open "http://localhost:$PORT" >/dev/null 2>&1 || true) &
exec .venv/bin/python run.py
