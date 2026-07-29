# Buscador de Processos JusBrasil (v1.1.0) — com OAB por UF — pacote standalone

Este ZIP é a versão standalone FastAPI/SerpAPI do agente CREAO `Buscador de Processos JusBrasil por Nome`.

> ⚠️ **Correção v1.1.1 do pacote standalone:** renomeado `app_standalone_fastapi.py` → `app.py` para o comando `uvicorn app:app` funcionar sem erro de "Could not import module 'app'".

## Conteúdo do ZIP (10 arquivos)

| Arquivo                                  | O que é                                                                                  |
|------------------------------------------|------------------------------------------------------------------------------------------|
| `app.py`                                 | **Servidor FastAPI** (rodar com `uvicorn app:app --port 8000`). Endpoints: `/`, `/api/search`, `/healthz`. |
| `index.html`                             | Frontend servido em `/`. Formulário com campo **UF** (27 estados) → manda `&uf=` ao `/api/search`. |
| `jusbrasil_search.py`                    | Lógica pura JusBrasil (slugify, build_query, find_jusbrasil_url, regex de totais).       |
| `oab_search.py`                          | Lógica OAB por UF (mapa UF→site da seccional, extract_oab_number, find_oab_url, format_oab). |
| `SKILL.md`                               | Skill descritiva do agente no CREAO (Goal, Inputs, Procedure step-by-step).              |
| `READMAgente_v1_1.md`                    | README interno do agente (descrição completa do fluxo CREAO).                            |
| `README.md`                              | Este arquivo (instruções de deploy).                                                     |
| `requirements.txt`                       | Dependências Python: `fastapi`, `uvicorn[standard]`, `httpx`.                            |
| `jusbrasil-website.html`                 | Site standalone HTML self-hosted (Tailwind CDN). Demo visual, abre direto no navegador. |
| `website_README.md`                      | README do site HTML.                                                                     |

## Como rodar localmente

```bash
# 1) Instalar dependências
pip install -r requirements.txt

# 2) Definir a chave SerpAPI (free tier: ~100 buscas/mês em https://serpapi.com)
export SERPAPI_KEY=sua_chave_aqui

# 3) Subir o servidor
uvicorn app:app --reload --port 8000

# 4) Abrir no navegador
# http://localhost:8000
```

> ⚠ O nome do arquivo de entrada DEVE ser `app.py` (literal). O `uvicorn app:app` procura pelo módulo `app`. No pacote zip anterior eu havia renomeado para `app_standalone_fastapi.py`, o que causava o erro `Could not import module "app"`.

## Endpoints da API

### `GET /api/search`

Parâmetros:
- `nome` (obrigatório): nome completo da pessoa.
- `uf` (opcional): sigla ou nome do estado. Ex: `SP`, `RJ`, `MG`, `São Paulo`.

Exemplos:

```
/api/search?nome=Juliana%20Carvalho%20Gomes
/api/search?nome=Juliana%20Carvalho%20Gomes&uf=MG
/api/search?nome=Jamila%20Drielly%20Moura%20Oliveira&uf=RR
```

Resposta (com `uf`):

```json
{
  "nome": "Juliana Carvalho Gomes",
  "slug_calculado": "juliana-carvalho-gomes",
  "google_query_jusbrasil": "\"Juliana Carvalho Gomes\" site:jusbrasil.com.br processos",
  "jusbrasil_url": "https://www.jusbrasil.com.br/processos/nome/28555609/juliana-carvalho-gomes",
  "jusbrasil_match_quality": "exact_slug_match",
  "total_processos": 290,
  "oab_uf_input": "MG",
  "oab": {
    "uf": "MG",
    "uf_input": "MG",
    "oab_site": "oabmg.org.br",
    "google_query_oab": "\"Juliana Carvalho Gomes\" site:oabmg.org.br MG",
    "oab_url": "https://www.oabmg.org.br/...",
    "oab_numero": "123456",
    "oab_formatado": "MG123456",
    "oab_match_quality": "exact_oab_profile_url"
  }
}
```

## Modos de falha (match_quality)

### JusBrasil
- `exact_slug_match` — slug bate (caso ideal).
- `slug_strip_match` — bate após remover hifens (variação de acento).
- `first_jusbrasil_match` — várias pessoas, primeira do Google.
- `no_jusbrasil_url_in_results` — sem página JusBrasil para esse nome.

### OAB
- `exact_oab_profile_url` — URL da seccional com slug exato do nome.
- `partial_oab_profile_url` — bate após remover hifens.
- `first_oab_site_url` — qualquer URL da seccional.
- `no_oab_url_in_results` — nenhuma URL da seccional veio do Google.
- `invalid_uf` — UF fora das 27 válidas. Resposta traz `oab.valid_ufs`.
- `uf_not_provided` — UF não foi enviada; só JusBrasil é consultado.

## Deploy

| Serviço   | Comando / passos                                                              |
|-----------|-------------------------------------------------------------------------------|
| **Render**| Push pro GitHub → New Web Service → Build `pip install -r requirements.txt` → Start `uvicorn app:app --host 0.0.0.0 --port $PORT` → env `SERPAPI_KEY` |
| **Railway**| `railway up`, depois `railway variables set SERPAPI_KEY=…`                  |
| **Fly.io**| `fly launch`, `fly secrets set SERPAPI_KEY=…`                                |
| **VPS**   | `uvicorn app:app --host 0.0.0.0 --port 8000` + nginx com TLS (Let's Encrypt) |

## Mudanças v1.0.0 → v1.1.1 (standalone)

- v1.1.0 (agente CREAO): adicionada consulta de OAB exata por UF, com campo opcional `uf` no formulário.
- v1.1.1 (este pacote standalone): renomeado `app_standalone_fastapi.py` → `app.py` (corrige `Could not import module "app"`), novo endpoint `/api/search?nome=...&uf=...`, novo `index.html` com seletor de UF.

## Teste rápido

```bash
curl "http://localhost:8000/api/search?nome=Juliana%20Carvalho%20Gomes&uf=MG"
```

Resposta esperada:
- `jusbrasil_url`: `https://www.jusbrasil.com.br/processos/nome/28555609/juliana-carvalho-gomes`
- `jusbrasil_match_quality`: `exact_slug_match`
- `total_processos`: `290`
- `oab.uf`: `MG`, `oab.oab_site`: `oabmg.org.br`
- `oab.oab_formatado`: `MG<6 dígitos>` (depende do resultado real)
