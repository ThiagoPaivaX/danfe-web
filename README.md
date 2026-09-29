📦 Sistema Integrado de Logística e Etiquetas SAP

Uma aplicação web (Middleware) desenvolvida para otimizar os processos logísticos e de impressão da operação diária. O sistema atua como uma ponte inteligente entre os ficheiros gerados pelo ERP (SAP) e as operações físicas nas docas e impressoras térmicas (Zebra).

Este projeto resolve duas grandes dores operacionais: a necessidade de reordenar milhares de notas de entrega com base em rotas logísticas e a necessidade de injetar dados dinâmicos (como validade) em etiquetas ZPL sem perder a formatação nativa.

✨ Funcionalidades Principais

1. Motor de OCR e Roteirização de Notas (Logística)

O SAP gera notas fiscais/pedidos de forma desordenada. Este módulo processa esses PDFs em massa:

🔍 Identificação Inteligente: Utiliza extração de texto (PyMuPDF) e normalização de strings para identificar endereços e nomes de lojas nas páginas.

🖃 Estampagem Visual (Watermark): Injeta o número da loja em vermelho na página (ex: LOJA: 18) para facilitar a separação visual pelos conferentes.

🛣️ Ordenação por Rotas Customizadas: Reordena as páginas do PDF final com base na rota de entrega configurada para cada setor (Mercearia, Perecíveis, FLV), poupando horas de organização manual.

2. Editor Dinâmico ZPL para Zebra (Produção)

O SAP exporta PDFs que "escondem" código ZPL. Editar isso manualmente quebraria a escala da etiqueta.

🛠️ Extração e Renderização: Usa pdf.js para extrair o código RAW ZPL e desenhá-lo num <canvas> HTML proporcional (104x150 mm).

📅 Injeção de Validade: Permite clicar na prévia visual para injetar uma Data de Validade e texto dinâmico (ex: VAL: 10/12/2026).

🖨️ Impressão em Massa: Adiciona comandos de quantidade (^PQ) e exporta um ficheiro .zpl nativo perfeito para as impressoras Zebra, garantindo 100% de precisão milimétrica e evitando o erro comum de "etiquetas gigantes" ou cortadas.

3. Autenticação e Perfis

Sistema de login simples e segmentado por setores (producao, mercearia, pereciveis, flv).

Cada setor gere a sua própria rota através de uma interface interativa (Drag & Drop ou listas).

🛠️️ Tecnologias Utilizadas

Backend:

Python 3

FastAPI: Framework moderno e de alta performance para a API e rotas web.

PyMuPDF (fitz): Biblioteca C/Python super rápida para manipulação, extração de texto e marcação de ficheiros PDF.

Frontend:

HTML5, CSS3, Vanilla JavaScript.

PDF.js: Processamento de PDF no lado do cliente (Client-side) para o motor ZPL.

Jinja2: Motor de templates integrado ao FastAPI.

🚀 Como Executar Localmente

Pré-requisitos

Python 3.8+ instalado.

Git instalado.

Passo a Passo

Clone o repositório:

git clone https://github.com/SeuUsuario/seu-repositorio.git
cd seu-repositorio


Crie e ative um ambiente virtual (Opcional, mas recomendado):

python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate


Instale as dependências:

pip install fastapi uvicorn pymupdf python-multipart jinja2


Inicie o servidor local:

uvicorn main:app --reload


Acesse a aplicação:
Abra o navegador e aceda a http://localhost:8000.

📁 Estrutura do Projeto

├── main.py               # Servidor FastAPI e lógica principal (Backend)
├── data/                 # Armazenamento JSON persistente das rotas por setor
├── uploads/              # Diretório temporário de ficheiros PDF enviados
├── output/               # Diretório temporário dos PDFs processados
├── static/               # Assets (style.css, scripts globais, ícones)
├── templates/            # Ficheiros HTML renderizados pelo Jinja2
│   ├── login.html        # Ecrã de autenticação
│   ├── setor.html        # Dashboard logístico (OCR e Roteirização)
│   └── validade.html     # Ferramenta ZPL (Produção Centralizada)
└── README.md             # Documentação do projeto


© 2026 - Desenvolvido por Thiago Paiva
