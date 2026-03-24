# docbuck

# 🚀 Project: Automated RAG Pipeline (WSL2 + n8n + Qdrant)

Questa roadmap delinea le fasi per costruire un sistema di Retrieval-Augmented Generation (RAG) 
professionale e scalabile utilizzando n8n come orchestratore e Qdrant come database vettoriale.

---

## 🛠️ Fase 1: Infrastruttura Core (Settimana 1)
*Obiettivo: Configurare l'ambiente Dockerizzato e i modelli base.*

- [ ] **Docker Compose Deployment**: Avviare lo stack (n8n, Qdrant, Open WebUI) con supporto GPU.
- [ ] **Volume Mapping**: Collegare `~/ai-cluster/data` al container n8n per l'ascolto dei file.
- [ ] **Model Preparation**: 
    - `ollama pull llama3` (Modello di generazione).
    - `ollama pull mxbai-embed-large` (Modello di embedding ad alta precisione).
- [ ] **Network Check**: Verificare che n8n riesca a "pingare" Qdrant e Ollama sulla rete `ai-network`.

---

## 📥 Fase 2: Pipeline di Ingestione (Settimana 1-2)
*Obiettivo: Automatizzare il passaggio "Documento -> Vettore".*

- [ ] **Trigger "Local Watcher"**: Configurare n8n per attivarsi ogni volta che un file entra nella cartella `/data`.
- [ ] **Advanced Parsing**: Integrare **Unstructured.io** (Docker) per estrarre testo pulito da PDF complessi e tabelle.
- [ ] **Chunking Strategy**: 
    - *Size*: 800 caratteri.
    - *Overlap*: 150 caratteri (per mantenere la continuità dei dati).
- [ ] **Vector Storage**: Creazione della "Collection" su Qdrant tramite n8n e caricamento dei vettori con metadati (filename, timestamp).

---

## 🧠 Fase 3: Retrieval & Chat Interface (Settimana 2-3)
*Obiettivo: Interrogare i documenti e ricevere risposte aggregate.*

- [ ] **Workflow "Search"**: Creare un workflow n8n che accetta una query e restituisce i chunk più rilevanti.
- [ ] **Top-K Tuning**: Impostare il recupero dinamico a **20 chunk** per coprire documenti multi-pagina.
- [ ] **Open WebUI Integration**: 
    - Configurare una **Function** o un **Action** in Open WebUI per chiamare il workflow di n8n.
- [ ] **System Prompt Engineering**: Definire le istruzioni per l'IA (es. "Analizza i dati dei pagamenti e genera tabelle riassuntive").

---

## ⚡ Fase 4: Optimization & Scaling (Settimana 3+)
*Obiettivo: Velocità "al volo" e precisione chirurgica.*

- [ ] **Ollama Keep-Alive**: Impostare `OLLAMA_KEEP_ALIVE=24h` per eliminare la latenza di caricamento modelli.
- [ ] **Reranking Node**: Aggiungere un nodo di Reranking in n8n per filtrare i risultati di Qdrant prima di darli all'LLM.
- [ ] **Hybrid Search**: Abilitare la ricerca Full-Text su Qdrant per trovare nomi e codici univoci non intercettati dalla ricerca semantica.
- [ ] **Metadata Filtering**: Permettere all'utente di filtrare la ricerca per "Sotto-cartella" o "Data".

---

## 📋 Stack Tecnologico
| Componente | Tool |
| :--- | :--- |
| **Engine** | Ollama (Llama 3) |
| **Orchestratore** | n8n |
| **Vector DB** | Qdrant |
| **Parsing** | Unstructured.io |
| **Frontend** | Open WebUI |


### Steps

## Configure ollama
# 1. Open your shell configuration file
nano ~/.bashrc

# 2. Add these lines at the end of the file
# OLLAMA_HOST=0.0.0.0 allows connections from any network interface (including Docker)
# OLLAMA_ORIGINS="*" permits cross-origin requests from any source
export OLLAMA_HOST=0.0.0.0
export OLLAMA_ORIGINS="*"

# 3. Save (Ctrl+O, Enter) and exit (Ctrl+X)

# 4. Apply the changes to the current session
source ~/.bashrc

# 5. Restart the Ollama service to apply the new configuration
# If you are using systemd (common on WSL2 Ubuntu):
sudo systemctl restart ollama

# If you run Ollama manually, use:
# killall ollama && ollama serve

## Configure n8n
Go to http://127.0.0.1:5678/setup and setup your account

Import template from n8n-template.json

Make sure you have mxbai-embed-large model on ollama: ollama pull mxbai-embed-large
