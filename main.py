# main.py
# Feito por Thiago Paiva
#
# esse arquivo é o servidor do sistema, é ele que recebe o pdf,
# lê as paginas, descobre qual loja é cada uma e devolve tudo organizado
#
# usei o fastapi pq aprendi que ele é bem simples de usar pra criar
# rotas e o pymupdf pra mexer nos pdfs


from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Form
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import fitz        # esse é o pymupdf, serve pra abrir e editar pdf
import unicodedata # esse remove os acentos das palavras
import uuid        # gera um codigo aleatorio pra nao ter dois arquivos com o mesmo nome
import os          # serve pra criar pastas e trabalhar com arquivos
import re          # serve pra limpar o texto, tipo remover virgula e ponto
import json        # serve pra salvar a rota em arquivo



app = FastAPI()

# essas sao as pastas que o sistema usa
# uploads = onde o pdf enviado fica temporariamente
# output = onde o pdf editado fica antes de baixar
# data = onde as rotas configuradas ficam salvas
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
DATA_FOLDER   = "data"

# cria as pastas se nao existirem ainda
# o exist_ok=True evita erro caso a pasta ja exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER,   exist_ok=True)

# conecta a pasta static (css, imagens) e a pasta templates (html)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# posicao onde o numero da loja vai aparecer no pdf
# x = distancia da esquerda, y = distancia do topo
# se precisar mudar o lugar, é só alterar esses dois numeros
POSICAO_X = 130
POSICAO_Y = 120


# usuarios e senhas de cada setor
# pra trocar a senha é só mudar o valor aqui e dar push no github
USUARIOS = {
    "producao":   "prod2026",
    "mercearia":  "merc2026",
    "pereciveis": "prec2026",
    "flv":        "flv2026",
}

# nome que aparece na tela pra cada setor
NOMES_SETORES = {
    "producao":   "Produção Centralizada",
    "mercearia":  "Mercearia",
    "pereciveis": "Perecíveis",
    "flv":        "FLV",
}


# aqui fica a lista de enderecos e o numero de cada loja
# a chave é a palavra que aparece no pdf e o valor é o numero da loja
#
# IMPORTANTE: os enderecos parecidos ficam la em cima pq a busca para
# no primeiro que encontrar. exemplo: "SAO CARLOS 3803" tem que vir
# antes de qualquer coisa com "SAO CARLOS" sozinho, senao pega errado
LOJAS = {

    # esses tem numero no endereco entao precisam vir antes
    "SAO CARLOS 3803":            "18",
    "SAO CARLOS 3200":            "32",
    "7 DE SETEMBRO 900":          "26",
    "7 DE SETEMBRO 214":          "27",
    "7 DE SETEMBRO 1256":         "29",

    # esses tem nomes parecidos entao coloquei variações
    "CAROLINA GERETO":            "14",
    "DALL QUA":                   "14",
    "DALLQUA":                    "14",

    # esses tem nomes um pouco esquisitos no pdf
    "GOVERNADOR PEDRO DE TOLEDO": "28",
    "AVENIDA INDUSTRIAL DR JOSE": "37",
    "INDUSTRIAL DR JOSE":         "37",

    # resto das lojas
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


# essa funcao limpa o texto pra poder comparar direito
# sem ela "São Carlos" e "SAO CARLOS" seriam diferentes, ai nao acharia
# ela remove acento, coloca tudo maiusculo e tira pontuacao
def normalizar(texto):
    # remove os acentos
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")

    # coloca tudo maiusculo
    texto = texto.upper()

    # remove tudo que nao for letra ou numero e troca por espaco
    texto = re.sub(r"[^A-Z0-9]", " ", texto)

    # se tiver varios espacos seguidos, vira um so
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


# essa funcao pega o texto de uma pagina e tenta descobrir qual loja é
# ela vai passando pelos enderecos do dicionario LOJAS até achar um que
# esteja dentro do texto da pagina
def identificar_loja(texto_da_pagina):
    texto_normalizado = normalizar(texto_da_pagina)

    for endereco, numero_loja in LOJAS.items():
        if normalizar(endereco) in texto_normalizado:
            # achou! para aqui e retorna o numero e o endereco
            return numero_loja, endereco

    # se nao achou nenhum, retorna 00
    return "00", "NAO IDENTIFICADO"


# essa funcao apaga um arquivo sem dar erro se ele nao existir
# uso ela pra limpar os arquivos temporarios depois de processar
def deletar_arquivo(caminho):
    try:
        os.remove(caminho)
    except FileNotFoundError:
        pass  # se nao achou o arquivo, ignora


# essa funcao le a rota salva de um setor
# a rota fica num arquivo json tipo: rota_pereciveis.json
# se nao tiver arquivo ainda, retorna uma lista vazia
def carregar_rota(setor):
    caminho = os.path.join(DATA_FOLDER, f"rota_{setor}.json")
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# essa funcao salva a nova rota no arquivo json do setor
def salvar_rota(setor, rota):
    caminho = os.path.join(DATA_FOLDER, f"rota_{setor}.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(rota, f, ensure_ascii=False)


# essa funcao ordena as paginas pela rota configurada
# as lojas que estao na rota ficam na ordem que foi configurada
# as lojas que nao estao na rota vao pro final em ordem crescente
#
# exemplo:
#   rota configurada = ["39", "41", "36"]
#   paginas do pdf   = [01, 36, 39, 41, 44]
#   resultado final  = [39, 41, 36, 01, 44]
def ordenar_por_rota(paginas, rota):
    na_rota      = []
    fora_da_rota = []

    for pagina in paginas:
        if pagina["numero"] in rota:
            na_rota.append(pagina)
        else:
            fora_da_rota.append(pagina)

    # ordena as que estao na rota pela posicao dela na lista
    na_rota.sort(key=lambda p: rota.index(p["numero"]))

    # ordena as que nao estao na rota em ordem crescente
    fora_da_rota.sort(key=lambda p: p["numero"])

    # primeiro as da rota, depois as outras
    return na_rota + fora_da_rota


# essa é a funcao principal que processa o pdf
# ela abre o pdf, passa por cada pagina, escreve o numero da loja
# e depois organiza tudo na ordem certa dependendo do setor
def processar_pdf(caminho_upload, caminho_saida, setor):
    doc = fitz.open(caminho_upload)
    paginas = []

    for indice, pagina in enumerate(doc):
        texto = pagina.get_text()
        numero_loja, endereco = identificar_loja(texto)

        # escreve o numero da loja na pagina em vermelho
        pagina.insert_text(
            (POSICAO_X, POSICAO_Y),
            f"LOJA: {numero_loja}",
            fontsize=14,
            color=(1, 0, 0)
        )

        # guarda o indice e numero dessa pagina pra ordenar depois
        paginas.append({
            "indice": indice,
            "numero": numero_loja,
        })

    # producao usa ordem crescente normal
    # os outros setores usam a rota que foi configurada
    if setor == "producao":
        paginas_ordenadas = sorted(paginas, key=lambda p: p["numero"])
    else:
        rota = carregar_rota(setor)
        if rota:
            paginas_ordenadas = ordenar_por_rota(paginas, rota)
        else:
            # se nao tiver rota configurada ainda, usa crescente mesmo
            paginas_ordenadas = sorted(paginas, key=lambda p: p["numero"])

    # monta o pdf final copiando as paginas na ordem certa
    pdf_final = fitz.open()
    for p in paginas_ordenadas:
        pdf_final.insert_pdf(doc, from_page=p["indice"], to_page=p["indice"])

    pdf_final.save(caminho_saida)
    pdf_final.close()
    doc.close()

    return paginas


# -------------------------------------------------------------------
# ROTAS DO SISTEMA
# cada rota é uma url que o sistema responde
# GET = usuario esta acessando a pagina
# POST = usuario esta enviando alguma coisa
# -------------------------------------------------------------------


# pagina de login - abre quando entra no site
@app.get("/")
async def pagina_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


# quando clica em entrar no login
# verifica se o usuario e senha batem e manda pro setor certo
@app.post("/login")
async def fazer_login(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    if usuario in USUARIOS and USUARIOS[usuario] == senha:
        # senha certa, manda pra pagina do setor
        return RedirectResponse(url=f"/setor/{usuario}", status_code=303)

    # senha errada, volta pro login com mensagem de erro
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        status_code=401,
        context={"erro": "Usuário ou senha incorretos."}
    )


# pagina de cada setor
# o {setor} na url muda dependendo de quem logou
# ex: /setor/mercearia, /setor/flv
@app.get("/setor/{setor}")
async def pagina_setor(request: Request, setor: str):
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


# recebe o pdf, processa e devolve editado pra baixar
@app.post("/upload/{setor}")
async def upload_pdf(setor: str, file: UploadFile = File(...)):
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos.")

    # coloca um codigo unico no nome pra evitar conflito entre usuarios
    nome_unico     = f"{uuid.uuid4().hex}_{file.filename}"
    caminho_upload = os.path.join(UPLOAD_FOLDER, nome_unico)
    caminho_saida  = os.path.join(OUTPUT_FOLDER, f"editado_{nome_unico}")

    conteudo = await file.read()
    with open(caminho_upload, "wb") as f:
        f.write(conteudo)

    try:
        paginas = processar_pdf(caminho_upload, caminho_saida, setor)

        numeros = sorted(set(p["numero"] for p in paginas))

        # define o nome do arquivo que vai aparecer no download
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
        # o finally sempre roda mesmo se der erro
        # uso pra garantir que o arquivo original seja apagado
        deletar_arquivo(caminho_upload)


# salva a rota configurada pelo usuario
# recebe um json tipo: {"rota": ["39", "41", "36"]}
@app.post("/rota/{setor}")
async def salvar_configuracao_rota(setor: str, request: Request):
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")

    if setor == "producao":
        raise HTTPException(status_code=400, detail="Produção usa ordem crescente fixa.")

    dados = await request.json()
    rota  = dados.get("rota", [])
    salvar_rota(setor, rota)

    return JSONResponse({"ok": True, "rota": rota})


# retorna a rota atual de um setor (usado pelo javascript da pagina)
@app.get("/rota/{setor}")
async def ler_rota(setor: str):
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")

    return JSONResponse({
        "setor":       setor,
        "rota":        carregar_rota(setor),
        "todas_lojas": sorted(set(LOJAS.values())),
    })
