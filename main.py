# main.py
# Desenvolvido por: Thiago Paiva

from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Form
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import fitz        
import unicodedata 
import uuid        
import os          
import re          
import json        
import zipfile
from typing import List

app = FastAPI()

# ==========================================
# CONFIGURAÇÕES E PASTAS
# ==========================================
UPLOAD_FOLDER = "uploads" 
OUTPUT_FOLDER = "output"  
DATA_FOLDER   = "data"    

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER,   exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

POSICAO_X = 130
POSICAO_Y = 120

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

LOJAS = {
    "SAO CARLOS 3803":            "18",
    "SAO CARLOS 3200":            "32",
    "7 DE SETEMBRO 900":          "26",
    "7 DE SETEMBRO 214":          "27",
    "7 DE SETEMBRO 1256":         "29",
    "CAROLINA GERETO":            "14",
    "DALL QUA":                   "14",
    "DALLQUA":                    "14",
    "GOVERNADOR PEDRO DE TOLEDO": "28",
    "AVENIDA INDUSTRIAL DR JOSE": "37",
    "INDUSTRIAL DR JOSE":         "37",
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
# FUNÇÕES CORE
# ==========================================
def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")
    texto = texto.upper()
    texto = re.sub(r"[^A-Z0-9]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()

def identificar_loja(texto_da_pagina: str) -> tuple:
    texto_normalizado = normalizar(texto_da_pagina)
    for endereco, numero_loja in LOJAS.items():
        if normalizar(endereco) in texto_normalizado:
            return numero_loja, endereco
    return "00", "NAO IDENTIFICADO"

def deletar_arquivo(caminho: str):
    try:
        os.remove(caminho)
    except FileNotFoundError:
        pass

def carregar_rota(setor: str) -> list:
    caminho = os.path.join(DATA_FOLDER, f"rota_{setor}.json")
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_rota(setor: str, rota: list):
    caminho = os.path.join(DATA_FOLDER, f"rota_{setor}.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(rota, f, ensure_ascii=False)

def ordenar_por_rota(paginas: list, rota: list) -> list:
    na_rota = [p for p in paginas if p["numero"] in rota]
    fora_da_rota = [p for p in paginas if p["numero"] not in rota]
    na_rota.sort(key=lambda p: rota.index(p["numero"]))
    fora_da_rota.sort(key=lambda p: p["numero"])
    return na_rota + fora_da_rota

def processar_multiplos_pdfs(caminhos_upload: List[str], caminho_saida_base: str, setor: str, separar_lojas: bool) -> tuple:
    doc_master = fitz.open()

    for caminho in caminhos_upload:
        doc_temp = fitz.open(caminho)
        doc_master.insert_pdf(doc_temp)
        doc_temp.close()

    paginas = []
    
    for indice, pagina in enumerate(doc_master):
        texto = pagina.get_text()
        numero_loja, endereco = identificar_loja(texto)

        pagina.insert_text((POSICAO_X, POSICAO_Y), f"LOJA: {numero_loja}", fontsize=14, color=(1, 0, 0))

        paginas.append({
            "indice": indice,
            "numero": numero_loja,
        })

    if separar_lojas:
        lojas_dict = {}
        for p in paginas:
            lojas_dict.setdefault(p["numero"], []).append(p)

        arquivos_gerados = []
        for loja, pags in lojas_dict.items():
            pdf_loja = fitz.open()
            pags.sort(key=lambda x: x["indice"])
            for p in pags:
                pdf_loja.insert_pdf(doc_master, from_page=p["indice"], to_page=p["indice"])

            nome_arquivo = f"Loja_{loja}.pdf"
            caminho_pdf_loja = os.path.join(OUTPUT_FOLDER, f"{uuid.uuid4().hex}_{nome_arquivo}")
            pdf_loja.save(caminho_pdf_loja)
            pdf_loja.close()
            arquivos_gerados.append((nome_arquivo, caminho_pdf_loja))

        caminho_zip = caminho_saida_base + ".zip"
        with zipfile.ZipFile(caminho_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for nome, caminho in arquivos_gerados:
                zipf.write(caminho, arcname=nome)

        for _, caminho in arquivos_gerados:
            deletar_arquivo(caminho)

        doc_master.close()
        return caminho_zip, "zip", arquivos_gerados

    else:
        if setor == "producao":
            paginas_ordenadas = sorted(paginas, key=lambda p: p["numero"])
        else:
            rota = carregar_rota(setor)
            if rota:
                paginas_ordenadas = ordenar_por_rota(paginas, rota)
            else:
                paginas_ordenadas = sorted(paginas, key=lambda p: p["numero"])

        pdf_final = fitz.open()
        for p in paginas_ordenadas:
            pdf_final.insert_pdf(doc_master, from_page=p["indice"], to_page=p["indice"])

        caminho_pdf = caminho_saida_base + ".pdf"
        pdf_final.save(caminho_pdf)
        pdf_final.close()
        doc_master.close()

        return caminho_pdf, "pdf", paginas

# ==========================================
# ROTAS DA API
# ==========================================
@app.get("/")
async def pagina_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def fazer_login(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    if usuario in USUARIOS and USUARIOS[usuario] == senha:
        return RedirectResponse(url=f"/setor/{usuario}", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", status_code=401, context={"erro": "Usuário ou senha incorretos."})

@app.get("/setor/{setor}")
async def pagina_setor(request: Request, setor: str):
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")
    return templates.TemplateResponse(request=request, name="setor.html", context={
        "setor":       setor,
        "nome_setor":  NOMES_SETORES[setor],
        "rota_atual":  carregar_rota(setor),
        "todas_lojas": sorted(set(LOJAS.values())),
    })

@app.get("/setor/{setor}/validade")
async def pagina_validade(request: Request, setor: str):
    if setor != "producao":
        raise HTTPException(status_code=404, detail="Página não encontrada.")
    return templates.TemplateResponse(request=request, name="validade.html", context={"setor": setor, "nome_setor": NOMES_SETORES[setor]})

@app.post("/upload/{setor}")
async def upload_pdf(setor: str, files: List[UploadFile] = File(..., alias="file"), separar_lojas: bool = Form(False)):
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")

    caminhos_upload = []
    try:
        for file in files:
            if not file.filename.lower().endswith(".pdf"):
                continue
            caminho_upload = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{file.filename}")
            conteudo = await file.read()
            with open(caminho_upload, "wb") as f:
                f.write(conteudo)
            caminhos_upload.append(caminho_upload)

        if not caminhos_upload:
            raise HTTPException(status_code=400, detail="Nenhum arquivo PDF válido foi enviado.")

        caminho_saida_base = os.path.join(OUTPUT_FOLDER, f"processado_{uuid.uuid4().hex}")
        caminho_final, tipo_saida, info = processar_multiplos_pdfs(caminhos_upload, caminho_saida_base, setor, separar_lojas)

        if tipo_saida == "zip":
            nome_download = f"{NOMES_SETORES[setor]} - Lojas Separadas.zip"
            media_type = "application/zip"
        else:
            numeros = sorted(set(p["numero"] for p in info))
            nome_download = f"Loja {numeros[0]}.pdf" if len(numeros) == 1 else f"{NOMES_SETORES[setor]} ({len(info)} lojas).pdf"
            media_type = "application/pdf"

        return FileResponse(path=caminho_final, filename=nome_download, media_type=media_type)

    except Exception as erro:
        raise HTTPException(status_code=500, detail=f"Erro ao processar: {str(erro)}")
    finally:
        for caminho in caminhos_upload:
            deletar_arquivo(caminho)

@app.post("/rota/{setor}")
async def salvar_configuracao_rota(setor: str, request: Request):
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")
    if setor == "producao":
        raise HTTPException(status_code=400, detail="Produção usa ordem crescente fixa.")
    dados = await request.json()
    salvar_rota(setor, dados.get("rota", []))
    return JSONResponse({"ok": True, "rota": dados.get("rota", [])})

@app.get("/rota/{setor}")
async def ler_rota(setor: str):
    if setor not in USUARIOS:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")
    return JSONResponse({"setor": setor, "rota": carregar_rota(setor), "todas_lojas": sorted(set(LOJAS.values()))})
