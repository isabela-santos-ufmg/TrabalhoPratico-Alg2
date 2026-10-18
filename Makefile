SYSTEM_PYTHON := $(shell which python3.12 2>/dev/null || \
                         which python3.11 2>/dev/null || \
                         which python3.10 2>/dev/null || \
                         which python3 2>/dev/null)

VENV_DIR = .venv
PYTHON   = $(VENV_DIR)/bin/python
PIP      = $(VENV_DIR)/bin/pip
PORT     = 8050

.PHONY: all venv install run clean purge help

all: run

help:
	@echo "Comandos disponíveis:"
	@echo "  make run     - Prepara o ambiente e inicia a aplicação (TUDO AUTOMÁTICO)"
	@echo "  make kill-port - Mata qualquer processo rodando na porta $(PORT)"
	@echo "  make clean   - Remove caches e temporários"
	@echo "  make purge   - Remove o ambiente virtual (.venv) para reiniciar do zero"

# Valida se o Python encontrado é compatível (3.10 a 3.12)
check-python:
	@if [ -z "$(SYSTEM_PYTHON)" ]; then \
		echo "[-] ERRO: Nenhum interpretador Python 3 encontrado na máquina."; \
		exit 1; \
	fi
	@echo "[+] Usando interpretador base: $(SYSTEM_PYTHON)"
	@$(SYSTEM_PYTHON) -c 'import sys; v = sys.version_info; \
		sys.exit(0 if (3, 9) <= (v.major, v.minor) < (3, 13) else 1)' || { \
		echo "[-] ERRO: Versao incompativel do Python ($$($(SYSTEM_PYTHON) --version))."; \
		echo "    Bibliotecas geoespaciais necessitam do Python 3.10, 3.11 ou 3.12."; \
		echo "    No Ubuntu/Debian execute: sudo apt install python3.11 python3.11-venv"; \
		exit 1; \
	}

# Cria o .venv automaticamente se não existir
venv: check-python
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "[+] Criando ambiente virtual isolado (.venv)..."; \
		$(SYSTEM_PYTHON) -m venv $(VENV_DIR) || { \
			echo "[-] ERRO: Falha ao criar o venv. Se estiver no Debian/Ubuntu, falta o pacote de venv:"; \
			echo "    sudo apt install python3-venv"; \
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

purge: clean
	@echo "[+] Destruindo ambiente virtual..."
	rm -rf $(VENV_DIR)