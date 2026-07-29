# Buscador de Processos JusBrasil por Nome (v1.1.0) — com OAB por Estado

Bundle compactado com tudo o que foi produzido neste agente: lógica pura Python, skill
descritiva para o CREAO agent runner, site standalone em HTML e um microsserviço FastAPI
de referência.

## Conteúdo do zip

| Arquivo                                  | O que é                                                                                  |
|------------------------------------------|------------------------------------------------------------------------------------------|
| `SKILL.md`                               | Skill descritiva do agente (Goal, Inputs, Strategy, Procedure, Failure modes). Lida pelo host CREAO. |
| `jusbrasil_search.py`                    | Lógica pura do JusBrasil: `slugify`, `build_query`, `find_jusbrasil_url`, regex de totais.|
| `oab_search.py`                          | **NOVO v1.1.0** — mapa UF→site da seccional (27 UFs), `normalize_uf`, regex OAB/<UF> com exclusão CNJ, ranking de URL. |
| `jusbrasil-website.html`                 | Site standalone self-hosted (Tailwind via CDN). Abre direto no navegador. Demonstra o pipeline e o caso Juliana Carvalho Gomes. |
| `app_standalone_fastapi.py`              | Microsserviço FastAPI de referência (usa SerpAPI). Adaptado do bundle inicial que você subiu. |
| `requirements.txt`                       | Dependências Python (fastapi, uvicorn, httpx) — usado só se você for rodar o FastAPI.   |
| `README.md`                              | Este arquivo.                                                                            |

## Como usar o agente no CREAO (recomendado)

1. `nome`: nome completo (obrigatório). Ex: `Juliana Carvalho Gomes`.
2. `uf`: sigla do estado (opcional, mas recomendado). Ex: `MG`.
   - Aceita sigla (`SP`) ou nome (`São Paulo`).
   - 27 UFs válidas: AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP, TO.
3. Sem `uf`: devolve só a URL JusBrasil (compatível com v1.0.0).
4. Com `uf`: devolve JusBrasil **e** OAB/<UF> na seccional correspondente.

## Como rodar o site standalone (HTML)

1. Abra `jusbrasil-website.html` no navegador (duplo clique), **ou**
2. Publique em qualquer host estático: GitHub Pages / Netlify Drop / Vercel / S3 / Cloudflare Pages.
3. **CORS bloqueia** o site de chamar o Google direto, então a busca real continua sendo feita via o agente CREAO. O site serve como **demo visual** do pipeline.

## Como rodar o microsserviço FastAPI (avançado, opcional)

Requer Python 3.11+ e uma chave SerpAPI (https://serpapi.com, free tier: ~100 buscas/mês).

```bash
pip install -r requirements.txt
export SERPAPI_KEY=sua_chave_aqui
uvicorn app_standalone_fastapi:app --reload --port 8000
```

Endpoints:
- `GET /` — frontend (não incluso nesse zip; use `app.py` completo do GitHub original).
- `GET /api/search?nome=<nome>&uf=<UF>` — busca JusBrasil e OAB e devolve JSON.
- `GET /healthz` — healthcheck.

## Mudanças v1.0.0 → v1.1.0

- Adicionada busca de OAB exata por estado (campo opcional `uf`).
- Novo helper `oab_search.py` (~11 KB, sem dependências externas).
- `SKILL.md` reescrito com Procedure step 5 + Failure modes da OAB.
- Form schema atualizado: novo campo `uf` (string, opcional).
- `persist_fields` agora inclui: `uf`, `oab_formatado`, `oab_url`, `oab_match_quality`.

## Notas de auditoria

- Nenhuma URL e nenhum número OAB são inventados — ambos vêm de `web_search` real.
- O regex OAB rejeita formatos CNJ (`NNNNNNN-DD.AAAA.J.TR.OOOO`) graças ao lookahead `(?![\\d\\-])`.
- Cada link da seccional é testado contra 4 níveis: `exact_oab_profile_url` → `partial_oab_profile_url` → `first_oab_site_url` → `no_oab_url_in_results`.

## Versão

- **v1.1.0** — adiciona OAB por UF + matcher rigoroso.
- Tag: `https://www.jusbrasil.com.br/processos/nome/28555609/juliana-carvalho-gomes` (caso demo: 290 processos, TJMG/TJDFT).
