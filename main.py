# ================================================================
# DANFE PROCESSOR - main.py
# ================================================================
# Sistema para:
# - receber um PDF DANFE
# - ler cada página
# - identificar a loja pelo endereço
# - escrever o número da loja no PDF
# - devolver o PDF editado
# ================================================================


# ================================================================
# IMPORTAÇÕES
# ================================================================

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import fitz
import unicodedata
import uuid
import os
import re


# ================================================================
# CONFIGURAÇÃO INICIAL
# ================================================================

app = FastAPI()

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# ================================================================
# POSIÇÃO DO TEXTO NO PDF
# X = esquerda para direita
# Y = cima para baixo
# ================================================================

POSICAO_X = 130
POSICAO_Y = 120


# ================================================================
# ENDEREÇOS DAS LOJAS
# ================================================================
# Chave = palavra/endereço que aparece no PDF
# Valor = número da loja
# ================================================================

LOJAS = {
    # Lojas com endereços parecidos ficam primeiro

    "SAO CARLOS 3803": "18",
    "SAO CARLOS 3200": "32",

    "7 DE SETEMBRO 900": "26",
    "7 DE SETEMBRO 214": "27",
    "7 DE SETEMBRO 1256": "29",

    "CAROLINA GERETO": "14",
    "DALL QUA": "14",
    "DALLQUA": "14",

    #LOJAS COM NOMES ESQUISITOS

    "GOVERNADOR PEDRO DE TOLEDO": "28",

    "AVENIDA INDUSTRIAL DR JOSE": "37",
    "INDUSTRIAL DR JOSE": "37",

    # Lojas normais

    "QUINZINHO": "01",
    "EDGAR FERRAZ": "02",
    "DAS NACOES": "03",
    "25 DE JANEIRO": "04",
    "SALIM SAHAO": "05",
    "ANTONIO BOTELHO": "06",
    "PADRE TEIXEIRA": "07",
    "VISCONDE DE PELOTAS": "08",
    "RAIMUNDO CORREA": "09",
    "CAPITAO LUIZ BRANDAO": "10",
    "FLORIANO PEIXOTO": "11",
    "FLORIANO SIMOES": "12",
    "JULIO DE FARIA": "13",
    "CAROLINA G DALLOQUA": "14",
    "DO CAFE": "15",
    "HUMAITA": "16",
    "SANTO ANTONIO": "17",
    "SANTA CATARINA": "19",
    "CATEDRAL": "20",
    "VOLUNTARIOS DA PATRIA": "21",
    "VISCONDE DE INHAUMA": "22",
    "XV DE NOVEMBRO": "23",
    "FELIX FAGUNDES": "24",
    "CAPITAO EMIDIO": "25",
    "GOVERNADOR DE TOLEDO": "28",
    "RIO BRANCO": "30",
    "FAUSTO LYRA BRANDAO": "31",
    "OLAVO BILAC": "33",
    "LARANJAL PAULISTA": "34",
    "TIRADENTES": "35",
    "DOM PEDRO": "36",
    "IRINEU ORTIGOZA": "37",
    "LUCIANO PACHECO": "38",
    "ANTONIA MUGNATTO": "39",
    "DONA CORINA": "40",
    "MARIA SPAGNOL GABALDO": "41",
    "MARIA THEREZA DE CONTE": "42",
    "REINALDO ANTONIO FANTI": "43",
    "BALDAN": "44",
    "BENEDITO CALIXTO": "45",
    "MAJOR HIPOLITO": "46",
    "VICENTE JOSE PARISE": "47",
}


# ================================================================
# FUNÇÃO PARA NORMALIZAR TEXTO
# ================================================================
# Ela deixa o texto mais fácil de comparar:
# - remove acentos
# - transforma em maiúsculo
# - remove pontuação
# - troca vários espaços por apenas um
# ================================================================

def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")
    texto = texto.upper()

    # Remove qualquer coisa que não seja letra ou número
    texto = re.sub(r"[^A-Z0-9]", " ", texto)

    # Remove espaços duplicados
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


# ================================================================
# FUNÇÃO PARA IDENTIFICAR A LOJA
# ================================================================

def identificar_loja(texto_do_pdf: str):
    texto_normalizado = normalizar(texto_do_pdf)

    for endereco, numero_loja in LOJAS.items():
        endereco_normalizado = normalizar(endereco)

        if endereco_normalizado in texto_normalizado:
            return numero_loja, endereco

    return "00", "NÃO IDENTIFICADO"


# ================================================================
# FUNÇÃO PARA APAGAR ARQUIVOS TEMPORÁRIOS
# ================================================================

def deletar_arquivo(caminho: str):
    try:
        os.remove(caminho)
    except FileNotFoundError:
        pass


# ================================================================
# ROTA PRINCIPAL
# Abre o site
# ================================================================

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


# ================================================================
# ROTA DE UPLOAD
# Processa o PDF
# ================================================================

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):

    # Só aceita PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Apenas arquivos PDF são aceitos."
        )

    # Gera nome único para evitar conflito
    nome_unico = f"{uuid.uuid4().hex}_{file.filename}"

    caminho_upload = os.path.join(UPLOAD_FOLDER, nome_unico)

    caminho_saida = os.path.join(
        OUTPUT_FOLDER,
        f"editado_{nome_unico}"
    )

    # Salva o PDF recebido
    conteudo = await file.read()

    with open(caminho_upload, "wb") as f:
        f.write(conteudo)

    try:
        # Abre o PDF
        doc = fitz.open(caminho_upload)

        lojas_encontradas = []

        # Analisa página por página
        for numero_pagina, pagina in enumerate(doc, start=1):

            texto_pagina = pagina.get_text()

            numero_loja, endereco = identificar_loja(texto_pagina)

            lojas_encontradas.append(numero_loja)

            # Escreve a loja na página atual
            pagina.insert_text(
                (POSICAO_X, POSICAO_Y),
                f"LOJA: {numero_loja}",
                fontsize=14,
                color=(1, 0, 0)
            )

        # Salva o PDF editado
        doc.save(caminho_saida)
        doc.close()

        # Define o nome do arquivo baixado
        lojas_unicas = sorted(set(lojas_encontradas))

        if len(lojas_unicas) == 1:
            nome_download = f"Loja {lojas_unicas[0]}.pdf"
        else:
            nome_download = "Lojas Processadas.pdf"

        return FileResponse(
            path=caminho_saida,
            filename=nome_download,
            media_type="application/pdf"
        )

    except Exception as erro:

        deletar_arquivo(caminho_upload)
        deletar_arquivo(caminho_saida)

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar o PDF: {str(erro)}"
        )

    finally:
        deletar_arquivo(caminho_upload)