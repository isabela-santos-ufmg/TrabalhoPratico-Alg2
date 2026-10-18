SHELL := /bin/bash

SYSTEM_PYTHON := $(shell which python3.12 2>/dev/null || \
                        which python3.11 2>/dev/null || \
                        which python3.10 2>/dev/null || \
                        which python3 2>/dev/null || \
                        which python 2>/dev/null)

VENV_DIR = .venv
PYTHON   = $(VENV_DIR)/bin/python
PIP      = $(VENV_DIR)/bin/pip
PORT     = 8050

.PHONY: all venv install run clean purge help check-python install-pyenv

all: run

help:
	@echo "Comandos disponíveis:"
	@echo "  make run     - Prepara o ambiente e inicia a aplicação (TUDO AUTOMÁTICO)"
	@echo "  make kill-port - Mata qualquer processo rodando na porta $(PORT)"
	@echo "  make clean   - Remove caches e temporários"
	@echo "  make purge   - Remove o ambiente virtual (.venv) para reiniciar do zero"

# Instala o pyenv e uma versão compatível do Python se nada for encontrado
install-pyenv:
	@echo "[!] Nenhum interpretador Python compatível encontrado. Instalando o pyenv..."
	@if ! command -v git &>/dev/null; then \
		echo "[-] ERRO: 'git' é necessário para instalar o pyenv. Instale o git e tente novamente."; \
		exit 1; \
	fi
	@if [ ! -d "$$HOME/.pyenv" ]; then \
		curl https://pyenv.run | bash; \
	fi
	@export PYENV_ROOT="$$HOME/.pyenv"; \
	export PATH="$$PYENV_ROOT/bin:$$PATH"; \
	eval "$$(pyenv init -)"; \
	echo "[+] Instalando Python 3.11.8 via pyenv (isso pode demorar alguns minutos)..."; \
	pyenv install -s 3.11.8; \
	pyenv local 3.11.8

# Valida se o Python encontrado é compatível (3.9 a 3.12)
check-python:
	@# Se não encontrou python ou a versão for inválida, tenta usar o pyenv se já existir ou instala
	@PYTHON_BIN="$(SYSTEM_PYTHON)"; \
	if [ -z "$$PYTHON_BIN" ] || ! $$PYTHON_BIN -c 'import sys; v = sys.version_info; sys.exit(0 if (3, 9) <= (v.major, v.minor) < (3, 13) else 1)' 2>/dev/null; then \
		if [ -d "$$HOME/.pyenv" ]; then \
			export PYENV_ROOT="$$HOME/.pyenv"; \
			export PATH="$$PYENV_ROOT/bin:$$PATH"; \
			eval "$$(pyenv init -)"; \
			if command -v pyenv &>/dev/null; then \
				PYTHON_BIN="$$(pyenv sh-which python 2>/dev/null || echo "")"; \
			fi; \
		fi; \
	fi; \
	if [ -z "$$PYTHON_BIN" ] || ! $$PYTHON_BIN -c 'import sys; v = sys.version_info; sys.exit(0 if (3, 9) <= (v.major, v.minor) < (3, 13) else 1)' 2>/dev/null; then \
		$(MAKE) install-pyenv; \
		export PYENV_ROOT="$$HOME/.pyenv"; \
		export PATH="$$PYENV_ROOT/bin:$$PATH"; \
		eval "$$(pyenv init -)"; \
		PYTHON_BIN="$$(pyenv sh-which python)"; \
	fi; \
	echo "SYSTEM_PYTHON := $$PYTHON_BIN" > .Makefile.resolved

# Inclui o python resolvido dinamicamente se existir
-include .Makefile.resolved

# Cria o .venv automaticamente se não existir
venv: check-python
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "[+] Criando ambiente virtual isolado (.venv) usando $(SYSTEM_PYTHON)..."; \
		$(SYSTEM_PYTHON) -m venv $(VENV_DIR) || { \
			echo "[-] ERRO: Falha ao criar o venv. Verifique se o pacote python3-venv está instalado."; \
			exit 1; \
		}; \
	fi

install: venv
	@if [ ! -f "$(VENV_DIR)/.installed" ]; then \
		echo "[+] Instalando/Atualizando dependencias..."; \
		$(PIP) install --upgrade pip setuptools wheel; \
		$(PIP) install -r requirements.txt && touch $(VENV_DIR)/.installed; \
		mkdir -p data/input data/output; \
	fi

geocode: install
	@echo "[+] Iniciando processo de geocodificação dos bares..."
	PYTHONPATH=. $(PYTHON) backend/geocodificar.py

kill-port:
	@echo "[+] Verificando se a porta $(PORT) está ocupada..."
	@fuser -k $(PORT)/tcp 2>/dev/null && echo "[+] Porta $(PORT) liberada com sucesso." || echo "[+] Porta $(PORT) já estava livre."

run: install kill-port
	@echo "[+] Iniciando o EntregaBH..."
	PORT=$(PORT) PYTHONPATH=. $(PYTHON) frontend/app.py

clean:
	@echo "[+] Limpando arquivos temporarios..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f .Makefile.resolved

purge: clean
	@echo "[+] Destruindo ambiente virtual..."
	rm -rf $(VENV_DIR)