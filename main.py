# ================================================================
# DANFE PROCESSOR - main.py
# ================================================================
# Sistema para:
# - receber um PDF DANFE com várias lojas
# - ler cada página separadamente
# - identificar a loja pelo endereço
# - escrever o número da loja em cada página
# - ordenar as páginas em ordem crescente de loja (NOVO)
# - devolver um único PDF organizado
# ================================================================
# Desenvolvido por: Thiago Paiva
# ================================================================


# ================================================================
# IMPORTAÇÕES
# ================================================================

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import fitz        # PyMuPDF  →  lê e edita PDFs
import unicodedata # remove acentos
import uuid        # gera nomes únicos para os arquivos
import os          # gerencia pastas e arquivos
import re          # expressões regulares (limpeza de texto)


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
# X = distância da esquerda
# Y = distância do topo
# Aumenta e Diminui o tamando da letra no pdf
# ================================================================

POSICAO_X = 130
POSICAO_Y = 120


# ================================================================
# ENDEREÇOS DAS LOJAS
# ================================================================
# Chave = palavra/endereço que aparece no PDF
# Valor = número da loja
#
# REGRA IMPORTANTE:
# Endereços parecidos entre si ficam NO TOPO da lista,
# pois a busca para no primeiro que encontrar.
# Ex: "SAO CARLOS 3803" vem antes de "SAO CARLOS"
# ================================================================

LOJAS = {

    # --- Endereços com numeração específica (se não ferra tudo) ---

    "SAO CARLOS 3803":           "18",
    "SAO CARLOS 3200":           "32",

    "7 DE SETEMBRO 900":         "26",
    "7 DE SETEMBRO 214":         "27",
    "7 DE SETEMBRO 1256":        "29",

    # --- Endereços com nomes irmãos, mas não são ---

    "CAROLINA GERETO":           "14",
    "DALL QUA":                  "14",
    "DALLQUA":                   "14",

    # --- Endereços com nomes esquisitos ---

    "GOVERNADOR PEDRO DE TOLEDO":"28",
    "AVENIDA INDUSTRIAL DR JOSE":"37",
    "INDUSTRIAL DR JOSE":        "37",

    # --- Demais lojas ---

    "QUINZINHO":                 "01",
    "EDGAR FERRAZ":              "02",
    "DAS NACOES":                "03",
    "25 DE JANEIRO":             "04",
    "SALIM SAHAO":               "05",
    "ANTONIO BOTELHO":           "06",
    "PADRE TEIXEIRA":            "07",
    "VISCONDE DE PELOTAS":       "08",
    "RAIMUNDO CORREA":           "09",
    "CAPITAO LUIZ BRANDAO":      "10",
    "FLORIANO PEIXOTO":          "11",
    "FLORIANO SIMOES":           "12",
    "JULIO DE FARIA":            "13",
    "CAROLINA G DALLOQUA":       "14",
    "DO CAFE":                   "15",
    "HUMAITA":                   "16",
    "SANTO ANTONIO":             "17",
    "SANTA CATARINA":            "19",
    "CATEDRAL":                  "20",
    "VOLUNTARIOS DA PATRIA":     "21",
    "VISCONDE DE INHAUMA":       "22",
    "XV DE NOVEMBRO":            "23",
    "FELIX FAGUNDES":            "24",
    "CAPITAO EMIDIO":            "25",
    "GOVERNADOR DE TOLEDO":      "28",
    "RIO BRANCO":                "30",
    "FAUSTO LYRA BRANDAO":       "31",
    "OLAVO BILAC":               "33",
    "LARANJAL PAULISTA":         "34",
    "TIRADENTES":                "35",
    "DOM PEDRO":                 "36",
    "IRINEU ORTIGOZA":           "37",
    "LUCIANO PACHECO":           "38",
    "ANTONIA MUGNATTO":          "39",
    "DONA CORINA":               "40",
    "MARIA SPAGNOL GABALDO":     "41",
    "MARIA THEREZA DE CONTE":    "42",
    "REINALDO ANTONIO FANTI":    "43",
    "BALDAN":                    "44",
    "BENEDITO CALIXTO":          "45",
    "MAJOR HIPOLITO":            "46",
    "VICENTE JOSE PARISE":       "47",
}


# ================================================================
# FUNÇÃO: NORMALIZAR TEXTO
# ================================================================
# Deixa o texto pronto para comparação:
#   "Av. São Carlos, 3200" → "AV SAO CARLOS 3200"
#
# O que ela faz:
#   1. Remove os acentos
#   2. Deixa tudo maiúsculo
#   3. Remove pontuação e caracteres especiais
#   4. Remove espaços duplicados
# ================================================================

def normalizar(texto: str) -> str:

    # Passo 1: remove acentos
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")

    # Passo 2: maiúsculo
    texto = texto.upper()

    # Passo 3: remove tudo que não for letra ou número
    texto = re.sub(r"[^A-Z0-9]", " ", texto)

    # Passo 4: remove espaços duplicados
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


# ================================================================
# FUNÇÃO: IDENTIFICAR LOJA
# ================================================================
# Recebe o texto de uma página e procura qual loja está lá.
#
# Retorna:
#   - número da loja  ex: "05"
#   - endereço achado ex: "SALIM SAHAO"
#
# Se não achar nenhuma, retorna ("00")
# ================================================================

def identificar_loja(texto_da_pagina: str) -> tuple:

    texto_normalizado = normalizar(texto_da_pagina)

    for endereco, numero_loja in LOJAS.items():
        endereco_normalizado = normalizar(endereco)

        if endereco_normalizado in texto_normalizado:
            # Achou! Para a busca e retorna
            return numero_loja, endereco

    # Não achou nenhuma loja conhecida
    return "00", "NÃO IDENTIFICADO"


# ================================================================
# FUNÇÃO: DELETAR ARQUIVO
# ================================================================
# Apaga um arquivo com segurança.
# Se o arquivo não existir, não dá erro.
# ================================================================

def deletar_arquivo(caminho: str):
    try:
        os.remove(caminho)
    except FileNotFoundError:
        pass


# ================================================================
# ROTA PRINCIPAL  →  GET /
# ================================================================
# Abre a página inicial do sistema no navegador.
# GET = o usuário está ACESSANDO a página (não enviando nada).
# ================================================================

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


# ================================================================
# ROTA DE UPLOAD  →  POST /upload/
# ================================================================
# Recebe o PDF, processa cada página, ordena e devolve.
# POST = o usuário está ENVIANDO dados (o arquivo PDF).
#
# Passo a passo:
#   1. Valida se é realmente um PDF
#   2. Salva com nome único (evita conflito entre usuários)
#   3. Abre o PDF e analisa página por página
#   4. Escreve o número da loja em cada página
#   5. Guarda o índice de cada página junto com o número da loja
#   6. Ordena as páginas pelo número da loja (crescente)
#   7. Monta um PDF novo já na ordem certa
#   8. Devolve o PDF para o usuário baixar
#   9. E por último corre para o abraço e seja feliz!
# ================================================================

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):

    # --- Passo 1: Só aceita PDF ---
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Apenas arquivos PDF são aceitos."
        )

    # --- Passo 2: Gera nome único para evitar conflito ---
    # uuid4().hex gera um código aleatório tipo "a3f2b1c4ef..."
    nome_unico    = f"{uuid.uuid4().hex}_{file.filename}"
    caminho_upload = os.path.join(UPLOAD_FOLDER, nome_unico)
    caminho_saida  = os.path.join(OUTPUT_FOLDER, f"editado_{nome_unico}")

    # Salva o PDF recebido no disco
    conteudo = await file.read()
    with open(caminho_upload, "wb") as f:
        f.write(conteudo)

    try:
        # --- Passo 3: Abre o PDF ---
        doc = fitz.open(caminho_upload)

        # Lista que vai guardar as informações de cada página
        # Exemplo de como vai ficar:
        # [
        #   {"indice": 0, "numero": "05"},
        #   {"indice": 1, "numero": "01"},
        #   {"indice": 2, "numero": "12"},
        # ]
        paginas = []

        for indice, pagina in enumerate(doc):

            # Extrai o texto só desta página
            texto_da_pagina = pagina.get_text()

            # Identifica a loja desta página
            numero_loja, endereco = identificar_loja(texto_da_pagina)

            # --- Passo 4: Escreve o número na página ---
            pagina.insert_text(
                (POSICAO_X, POSICAO_Y),
                f"LOJA: {numero_loja}",
                fontsize=14,
                color=(1, 0, 0)  # vermelho (R=1, G=0, B=0)
            )

            # --- Passo 5: Guarda o índice e o número desta página ---
            paginas.append({
                "indice": indice,
                "numero": numero_loja,
            })

        # --- Passo 6: Ordena as páginas pelo número da loja ---
        # sorted() organiza a lista em ordem crescente
        # key=lambda p: p["numero"] → ordena pelo campo "numero"
        # "00" (não identificadas) vem primeiro automaticamente
        paginas_ordenadas = sorted(paginas, key=lambda p: p["numero"])

        # --- Passo 7: Monta um PDF novo com as páginas na ordem certa ---
        pdf_final = fitz.open()  # cria um PDF vazio

        for pagina_info in paginas_ordenadas:

            # Pega o índice original desta página
            indice_original = pagina_info["indice"]

            # Copia a página (já editada) para o PDF final
            pdf_final.insert_pdf(
                doc,
                from_page=indice_original,
                to_page=indice_original,
            )

        # Salva o PDF final
        pdf_final.save(caminho_saida)
        pdf_final.close()
        doc.close()

        # --- Passo 8: Define o nome do arquivo para download ---
        # Pega os números únicos encontrados para montar o nome
        numeros_encontrados = sorted(set(p["numero"] for p in paginas))

        if len(numeros_encontrados) == 1:
            # Só tinha uma loja → nome simples
            nome_download = f"Loja {numeros_encontrados[0]}.pdf"
        else:
            # Várias lojas → mostra a quantidade
            nome_download = f"DANFEs Organizados ({len(paginas)} lojas).pdf"

        # --- Devolve o PDF para o usuário baixar ---
        return FileResponse(
            path=caminho_saida,
            filename=nome_download,
            media_type="application/pdf"
        )

    except Exception as erro:
        # Se algo deu errado, apaga os arquivos e mostra o erro
        deletar_arquivo(caminho_upload)
        deletar_arquivo(caminho_saida)

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar o PDF: {str(erro)}"
        )

    finally:
        # "finally" SEMPRE executa, mesmo se der erro
        # Apaga o arquivo original para não acumular lixo no servidor
        deletar_arquivo(caminho_upload)