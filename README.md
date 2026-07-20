<div align="center">

# 📄 DANFE Processor

**Automatizando a organização de notas fiscais eletrônicas, uma página por vez.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-PDF%20Engine-red?style=flat)
![Status](https://img.shields.io/badge/status-em%20evolução-yellow)

</div>

---

## 💡 Sobre o projeto

No dia a dia do meu trabalho, todo lote de entrega chega em um único PDF com as DANFEs de várias lojas misturadas — e alguém precisava abrir, ler nota por nota e separar manualmente qual página era de qual loja. Um processo repetitivo, lento e sujeito a erro.

O **DANFE Processor** resolve isso: você sobe o PDF, o sistema lê o endereço de cada nota, identifica automaticamente a loja correspondente, carimba o número dela na página e devolve tudo já organizado em ordem crescente. O que levava minutos manuseando papel (ou PDF) agora leva segundos.

## ⚙️ Como funciona

```
PDF com várias DANFEs
        │
        ▼
  Lê o texto de cada página
        │
        ▼
  Compara o endereço com a base de lojas cadastradas
        │
        ▼
  Escreve "LOJA: XX" na página
        │
        ▼
  Reordena as páginas por número de loja
        │
        ▼
  Devolve um único PDF organizado
```

## ✨ Funcionalidades

- 📤 Upload simples via navegador, sem instalação nada para o usuário final
- 🔎 Identificação automática da loja pelo endereço presente na nota
- 🏷️ Marcação visual do número da loja em cada página
- 🔢 Reordenação automática das páginas por loja
- 📎 Nome de arquivo final adaptado à quantidade de lojas encontradas
- 🧹 Limpeza automática de arquivos temporários após o processamento

## 🛠️ Tecnologias

| Camada       | Ferramenta                          |
|--------------|--------------------------------------|
| Backend      | Python + FastAPI                     |
| Manipulação de PDF | PyMuPDF (fitz)                 |
| Templates    | Jinja2                               |
| Frontend     | HTML + CSS                           |
| Deploy       | Render                               |

## 🚀 Rodando localmente

```bash
git clone https://github.com/ThiagoPaivaX/danfe-web.git
cd danfe-web
pip install -r requirements.txt
uvicorn main:app --reload
```

Depois é só acessar `http://localhost:8000` no navegador e enviar um PDF.

## 📂 Estrutura do projeto

```
danfe-web/
├── main.py              # lógica principal: leitura, identificação e organização
├── templates/
│   └── index.html       # página de upload
├── static/
│   └── style.css        # estilo da interface
├── requirements.txt
└── render.yaml           # configuração de deploy
```

## 🗺️ Próximos passos

- [ ] Validar o tipo real do arquivo enviado, não só a extensão
- [ ] Painel para cadastrar/editar lojas sem mexer no código
- [ ] Testes automatizados

## 👤 Autor

Feito por **Thiago Paiva** — estudante de Engenharia de Software, aprendendo Python e FastAPI resolvendo problemas reais do trabalho.

[GitHub](https://github.com/ThiagoPaivaX)
