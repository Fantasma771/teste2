"""
Servidor FastAPI para o Buscador de Processos JusBrasil (com OAB por UF).

Endpoints:
    GET /                        -> serve index.html (frontend com formulário)
    GET /api/search?nome=&uf=    -> JusBrasil + opcionalmente OAB na seccional da UF
    GET /healthz                 -> healthcheck

Variáveis de ambiente:
    SERPAPI_KEY                  -> obrigatória (cadastro grátis em serpapi.com)

Execução local:
    pip install -r requirements.txt
    export SERPAPI_KEY=sua_chave
    uvicorn app:app --reload --port 8000
"""
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from jusbrasil_search import (
    build_query as jb_build_query,
    extract_total_processos,
    find_jusbrasil_url,
    slugify as jb_slugify,
)
from oab_search import (
    OAB_SITES,
    build_query as oab_build_query,
    extract_oab_number,
    find_oab_url,
    format_oab,
    normalize_uf,
)

SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
STATIC_DIR = Path(__file__).parent

app = FastAPI(
    title="Buscador de Processos JusBrasil (com OAB por UF)",
    description="Dado um nome + UF opcional, devolve URL JusBrasil canônica e OAB exata na seccional.",
    version="1.1.0",
)

# CORS permissivo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _require_key():
    if not SERPAPI_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "SERPAPI_KEY não configurada. Defina a variável de ambiente "
                "SERPAPI_KEY no host (ex: Render → Environment → Add env var)."
            ),
        )


async def serpapi_search(query: str, num: int = 10):
    """Wrapper SerpAPI. Devolve lista [{title, url, description}, ...]."""
    _require_key()
    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num,
        "gl": "br",
        "hl": "pt-BR",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(SERPAPI_ENDPOINT, params=params)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"SerpAPI respondeu {resp.status_code}: {resp.text[:300]}",
        )
    data = resp.json()
    organic = data.get("organic_results") or []
    flat = []
    for r in organic:
        flat.append({
            "title": r.get("title", ""),
            "url": r.get("link") or r.get("url") or "",
            "description": r.get("snippet") or r.get("snippet_highlighted_words_text") or "",
        })
    return flat


def _empty_oab_block(reason: str):
    """Devolve bloco OAB padronizado para casos vazios / falhas."""
    return {
        "uf": None,
        "uf_input": None,
        "oab_url": None,
        "oab_numero": None,
        "oab_formatado": None,
        "oab_match_quality": reason,
        "oab_site": None,
    }


@app.get("/api/search")
async def search(nome: str, uf: str | None = None):
    nome = (nome or "").strip()
    if len(nome) < 3:
        raise HTTPException(
            status_code=400,
            detail="Nome deve ter ao menos 3 caracteres.",
        )

    # ===== JusBrasil (sempre) =====
    slug = jb_slugify(nome)
    query_jb = jb_build_query(nome)
    results_jb = await serpapi_search(query_jb)
    jusbrasil_url, jusbrasil_match = find_jusbrasil_url(results_jb, slug)
    total_processos = extract_total_processos(results_jb)

    out = {
        "nome": nome,
        "slug_calculado": slug,
        "google_query_jusbrasil": query_jb,
        "jusbrasil_url": jusbrasil_url,
        "jusbrasil_match_quality": jusbrasil_match,
        "total_processos": total_processos,
        # Bloco OAB — preenchido abaixo se `uf` válido.
        "oab_uf_input": uf,
    }

    # ===== OAB (opcional) =====
    if not uf or not uf.strip():
        out["oab"] = _empty_oab_block("uf_not_provided")
        return JSONResponse(out)

    uf_norm = normalize_uf(uf)
    if not uf_norm:
        # UF inválida: devolve todas as UFs válidas para o cliente exibir.
        valid_ufs = sorted(OAB_SITES.keys())
        out["oab"] = {
            **(_empty_oab_block("invalid_uf")),
            "valid_ufs": valid_ufs,
        }
        return JSONResponse(out)

    # UF válida — busca Google + extração OAB.
    query_oab = oab_build_query(nome, uf_norm)
    try:
        results_oab = await serpapi_search(query_oab)
    except HTTPException as e:
        # Propaga erro do SerpAPI mas mantém JusBrasil já calculado.
        out["oab"] = _empty_oab_block(f"serpapi_error:{e.status_code}")
        return JSONResponse(out)

    slide_slug = jb_slugify(nome)
    oab_url, oab_match = find_oab_url(results_oab, slide_slug, uf_norm)
    blob = " ".join(
        (r.get("title", "") + " " + r.get("description", "")) for r in results_oab
    )
    oab_num = extract_oab_number(blob, uf_norm)
    oab_fmt = format_oab(oab_num, uf_norm) if oab_num else None

    out["oab"] = {
        "uf": uf_norm,
        "uf_input": uf,
        "oab_site": OAB_SITES[uf_norm],
        "google_query_oab": query_oab,
        "oab_url": oab_url,
        "oab_numero": oab_num,
        "oab_formatado": oab_fmt,
        "oab_match_quality": oab_match,
    }
    return JSONResponse(out)


@app.get("/healthz")
async def healthz():
    _require_key()
    valid_ufs = sorted(OAB_SITES.keys())
    return {
        "status": "ok",
        "serpapi_key_set": bool(SERPAPI_KEY),
        "valid_ufs": valid_ufs,
        "agent_version": "1.1.0",
    }


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")
