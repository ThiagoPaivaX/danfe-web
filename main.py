# main.py
# Desenvolvido por: Thiago Paiva
#
# Servidor principal da aplicação de gestão e emissão de etiquetas/notas.
# Responsável por processar os PDFs do SAP, realizar o OCR/extração de texto,
# identificar o número das lojas, estampar a identificação no documento e 
# reordenar as páginas com base em rotas logísticas pré-configuradas.

from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Form
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import fitz        # PyMuPDF: Motor de leitura e manipulação de arquivos PDF
import unicodedata # Utilizado para higienização e normalização de strings (remoção de acentos)
import uuid        # Geração de hashes únicos para evitar sobrescrita de arquivos simultâneos
import os          # Manipulação do sistema de ficheiros (criação de diretórios)
import re          # Expressões regulares para limpeza de pontuações no texto do PDF
import json        # Serialização de dados para persistência das rotas logísticas

app = FastAPI()

# ==========================================
# CONFIGURAÇÕES DE DIRETÓRIOS E AMBIENTE
# ==========================================
UPLOAD_FOLDER = "uploads" # Armazenamento temporário de PDFs recebidos
OUTPUT_FOLDER = "output"  # Armazenamento de PDFs processados e prontos para download
DATA_FOLDER   = "data"    # Persistência de ficheiros JSON (rotas dos setores)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER,   exist_ok=True)

# Montagem dos arquivos estáticos (CSS/JS) e templates HTML
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Coordenadas (em pontos) para a estampagem da identificação da loja no PDF
POSICAO_X = 130
POSICAO_Y = 120

# ==========================================
# DADOS DE AUTENTICAÇÃO E SETORES
# ==========================================
USUARIOS = {
    "producao":   "prod2026",
    "mercearia":  "merc2026",
    "pereciveis": "prec2026",
    "flv":        "flv2026",
}

NOMES_SETORES = {
    "producao":   "Produção Centralizada",
    "mercearia":  "Mercearia",
    "pereciveis": "Perecíveis",
    "flv":        "FLV",
}

# Dicionário de mapeamento: Endereço (Chave) -> Número da Loja (Valor)
# IMPORTANTE: A ordem importa. Endereços mais específicos ou com numeração 
# devem ser declarados primeiro para garantir precisão no algoritmo de busca (Greedy Match).
LOJAS = {
    # Endereços com numeração (Alta especificidade)
    "SAO CARLOS 3803":            "18",
    "SAO CARLOS 3200":            "32",
    "7 DE SETEMBRO 900":          "26",
    "7 DE SETEMBRO 214":          "27",
    "7 DE SETEMBRO 1256":         "29",

    # Variações de nomenclatura no SAP
    "CAROLINA GERETO":            "14",
    "DALL QUA":                   "14",
    "DALLQUA":                    "14",
    "GOVERNADOR PEDRO DE TOLEDO": "28",
    "AVENIDA INDUSTRIAL DR JOSE": "37",
    "INDUSTRIAL DR JOSE":         "37",

    # Endereços genéricos / Lojas padrão
    "QUINZINHO":                  "01",
    "EDGAR FERRAZ":               "02",
    "DAS NACOES":                 "03",
    "25 DE JANEIRO":              "04",
    "SALIM SAHAO":                "05",
    "ANTONIO BOTELHO":            "06",
    "PADRE TEIXEIRA":             "07",
    "VISCONDE DE PELOTAS":        "08",
    "RAIMUNDO CORREA":            "09",
    "CAPITAO LUIZ BRANDAO":       "10",
    "FLORIANO PEIXOTO":           "11",
    "FLORIANO SIMOES":            "12",
    "JULIO DE FARIA":             "13",
    "CAROLINA G DALLOQUA":        "14",
    "DO CAFE":                    "15",
    "HUMAITA":                    "16",
    "SANTO ANTONIO":              "17",
    "SANTA CATARINA":             "19",
    "CATEDRAL":                   "20",
    "VOLUNTARIOS DA PATRIA":      "21",
    "VISCONDE DE INHAUMA":        "22",
    "XV DE NOVEMBRO":             "23",
    "FELIX FAGUNDES":             "24",
    "CAPITAO EMIDIO":             "25",
    "GOVERNADOR DE TOLEDO":       "28",
    "RIO BRANCO":                 "30",
    "FAUSTO LYRA BRANDAO":        "31",
    "OLAVO BILAC":                "33",
    "LARANJAL PAULISTA":          "34",
    "TIRADENTES":                 "35",
    "DOM PEDRO":                  "36",
    "IRINEU ORTIGOZA":            "37",
    "LUCIANO PACHECO":            "38",
    "ANTONIA MUGNATTO":           "39",
    "DONA CORINA":                "40",
    "MARIA SPAGNOL GABALDO":      "41",
    "MARIA THEREZA DE CONTE":     "42",
    "REINALDO ANTONIO FANTI":     "43",
    "BALDAN":                     "44",
    "BENEDITO CALIXTO":           "45",
    "MAJOR HIPOLITO":             "46",
    "VICENTE JOSE PARISE":        "47",
    "RUA CARLOS PULICI":          "49",
}

# ==========================================
# FUNÇÕES DE PROCESSAMENTO CORE
# ==========================================

def normalizar(texto: str) -> str:
    """
    Higieniza a string removendo acentuação, caracteres especiais e espaços duplicados.
    Garante que as comparações de string entre o PDF e o dicionário sejam perfeitas.
    """
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")
    texto = texto.upper()
    texto = re.sub(r"[^A-Z0-9]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()

def identificar_loja(texto_da_pagina: str) -> tuple:
    """
    Percorre o dicionário de lojas e procura correspondências no texto da página do PDF.
    Retorna uma tupla contendo (numero_da_loja, endereco_encontrado).
    """
    texto_normalizado = normalizar(texto_da_pagina)
    for endereco, numero_loja in LOJAS.items():
        if normalizar(endereco) in texto_normalizado:
            return numero_loja, endereco
    return "00", "NAO IDENTIFICADO"

def deletar_arquivo(caminho: str):
    """
    Remove arquivos temporários do sistema sem lançar exceções caso o arquivo não exista.
    """
    try:
        os.remove(caminho)
    except FileNotFoundError:
        pass

def carregar_rota(setor: str) -> list:
    """
    Recupera a rota logística (ordem de lojas) configurada pelo usuário via JSON.
    """
    caminho = os.path.join(DATA_FOLDER, f"rota_{setor}.json")
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_rota(setor: str, rota: list):
    """
    Persiste a nova ordem logística configurada para o setor no ficheiro JSON.
    """
    caminho = os.path.join(DATA_FOLDER, f"rota_{setor}.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(rota, f, ensure_ascii=False)

def ordenar_por_rota(paginas: list, rota: list) -> list:
    """
    Algoritmo de ordenação que divide as páginas em dois grupos:
    1. Páginas cujas lojas constam na rota (ordenadas pela indexação da rota).
    2. Páginas ignoradas/fora da rota (ordenadas alfabética/numericamente no final do arquivo).
    """
    na_rota      = []
    fora_da_rota = []

    for pagina in paginas:
        if pagina["numero"] in rota:
            na_rota.append(pagina)
        else:
            fora_da_rota.append(pagina)

    na_rota.sort(key=lambda p: rota.index(p["numero"]))
    fora_da_rota.sort(key=lambda p: p["numero"])

    return na_rota + fora_da_rota

def processar_pdf(caminho_upload: str, caminho_saida: str, setor: str) -> list:
    """
    Fluxo principal de manipulação do PDF:
    - Abre o documento e itera página por página.
    - Identifica a loja correspondente e estampa a numeração visualmente.
    - Reordena todas as páginas com base no setor e rota configurada.
    - Gera e salva o PDF final reordenado.
    """
    doc = fitz.open(caminho_upload)
    paginas = []

    for indice, pagina in enumerate(doc):
        texto = pagina.get_text()
        numero_loja, endereco = identificar_loja(texto)

        # Injeção do selo de identificação visual da loja no documento
        pagina.insert_text(
            (POSICAO_X, POSICAO_Y),
            f"LOJA: {numero_loja}",
            fontsize=14,
            color=(1, 0, 0) # Estampado a vermelho para contraste na impressão
        )

        paginas.append({
            "indice": indice,
            "numero": numero_loja,
        })

    # Aplicação da lógica de Roteirização/Ordenação
    if setor == "producao":
        paginas_ordenadas = sorted(paginas, key=lambda p: p["numero"])
    else:
        rota = carregar_rota(setor)
        if rota:
            paginas_ordenadas = ordenar_por_rota(paginas, rota)
        else:
            paginas_ordenadas = sorted(paginas, key=lambda p: p["numero"])

    # Reconstrução do documento final na nova ordem
    pdf_final = fitz.open()
    for p in paginas_ordenadas:
        pdf_final.insert_pdf(doc, from_page=p["indice"], to_page=p["indice"])

    pdf_final.save(caminho_saida)
    pdf_final.close()
    doc.close()

    return paginas

# ==========================================
# ENDPOINTS (ROTAS DA API FASTAPI)
# ==========================================

@app.get("/")
async def pagina_login(request: Request):
    """Renderiza a página inicial (Login)."""
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def fazer_login(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    """Valida as credenciais e redireciona o usuário para o dashboard do seu setor."""
    if usuario in USUARIOS and USUARIOS[usuario] == senha:
        return RedirectResponse(url=f"/setor/{usuario}", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        status_code=401,
        context={"erro": "Usuário ou senha incorretos."}
    )

@app.get("/setor/{setor}")
async def pagina_setor(request: Request, setor: str):
    """Carrega o dashboard principal de ordenação e roteirização do setor especificado."""
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")

    rota_atual = carregar_rota(setor)

    return templates.TemplateResponse(
        request=request,
        name="setor.html",
        context={
            "setor":       setor,
            "nome_setor":  NOMES_SETORES[setor],
            "rota_atual":  rota_atual,
            "todas_lojas": sorted(set(LOJAS.values())),
        }
    )

@app.get("/setor/{setor}/validade")
async def pagina_validade(request: Request, setor: str):
    """
    Acesso restrito à ferramenta de manipulação de etiquetas ZPL.
    Disponível exclusivamente para a Produção Centralizada.
    """
    if setor != "producao":
        raise HTTPException(status_code=404, detail="Página não encontrada.")

    return templates.TemplateResponse(
        request=request,
        name="validade.html",
        context={
            "setor":      setor,
            "nome_setor": NOMES_SETORES[setor],
        }
    )

@app.post("/upload/{setor}")
async def upload_pdf(setor: str, file: UploadFile = File(...)):
    """
    Recebe o ficheiro PDF do cliente, envia para o motor de processamento (processar_pdf)
    e retorna o documento editado e reordenado como anexo de download.
    """
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos.")

    # Gera um identificador único (UUID) para prevenir colisão de arquivos concorrentes
    nome_unico     = f"{uuid.uuid4().hex}_{file.filename}"
    caminho_upload = os.path.join(UPLOAD_FOLDER, nome_unico)
    caminho_saida  = os.path.join(OUTPUT_FOLDER, f"editado_{nome_unico}")

    conteudo = await file.read()
    with open(caminho_upload, "wb") as f:
        f.write(conteudo)

    try:
        paginas = processar_pdf(caminho_upload, caminho_saida, setor)
        numeros = sorted(set(p["numero"] for p in paginas))

        # Formatação inteligente do nome de saída baseada no conteúdo
        if len(numeros) == 1:
            nome_download = f"Loja {numeros[0]}.pdf"
        else:
            nome_download = f"{NOMES_SETORES[setor]} ({len(paginas)} lojas).pdf"

        return FileResponse(
            path=caminho_saida,
            filename=nome_download,
            media_type="application/pdf"
        )

    except Exception as erro:
        deletar_arquivo(caminho_upload)
        deletar_arquivo(caminho_saida)
        raise HTTPException(status_code=500, detail=f"Erro ao processar: {str(erro)}")

    finally:
        # Garante a limpeza da memória/storage apagando os ficheiros não editados
        deletar_arquivo(caminho_upload)

@app.post("/rota/{setor}")
async def salvar_configuracao_rota(setor: str, request: Request):
    """Recebe um payload JSON do frontend para persistir uma nova ordem logística."""
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")

    if setor == "producao":
        raise HTTPException(status_code=400, detail="Produção usa ordem crescente fixa.")

    dados = await request.json()
    rota  = dados.get("rota", [])
    salvar_rota(setor, rota)

    return JSONResponse({"ok": True, "rota": rota})

@app.get("/rota/{setor}")
async def ler_rota(setor: str):
    """Devolve a rota logística guardada para renderização dinâmica no frontend."""
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")

    return JSONResponse({
        "setor":       setor,
        "rota":        carregar_rota(setor),
        "todas_lojas": sorted(set(LOJAS.values())),
    })
