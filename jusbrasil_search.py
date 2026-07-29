#!/usr/bin/env python3
"""
Buscador de páginas JusBrasil por nome.

Estratégia:
1. Normalizar o nome (slug) para comparar com a URL.
2. Buscar no Google com filtro site:jusbrasil.com.br
3. Filtrar resultados cujo URL bate com /processos/nome/{id}/{slug}
4. Preferir o match exato de slug; cair para o primeiro JusBrasil válido.
"""
import json
import re
import sys
import unicodedata
from urllib.parse import quote_plus, urlparse

JUSBRASIL_PATTERN = re.compile(
    r"^https?://(?:www\.)?jusbrasil\.com\.br/processos/nome/(\d+)/([\w\-]+)/?$"
)


def slugify(name: str) -> str:
    """Normaliza nome para slug (igual JusBrasil: lowercase, sem acento, hífens)."""
    nfkd = unicodedata.normalize("NFKD", name)
    only_ascii = "".join(c for c in nfkd if not unicodedata.combining(c))
    only_ascii = only_ascii.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", only_ascii).strip("-").lower()
    return cleaned


def build_query(name: str) -> str:
    """Constrói a query de busca: nome entre aspas + filtro de site + processos."""
    quoted = f'"{name.strip()}"'
    return f"{quoted} site:jusbrasil.com.br processos"


def find_jusbrasil_url(results: list, expected_slug: str) -> tuple[str | None, str]:
    """Varre resultados e devolve (url, motivo_da_escolha)."""
    matches = []
    for r in results:
        url = r.get("url", "")
        m = JUSBRASIL_PATTERN.match(url)
        if not m:
            continue
        _id, slug = m.group(1), m.group(2)
        matches.append((url, slug, _id))

    if not matches:
        return None, "no_jusbrasil_url_in_results"

    # 1) match exato de slug → preferido
    for url, slug, _id in matches:
        if slug == expected_slug:
            return url, "exact_slug_match"

    # 2) match mais próximo (slug igual ao esperado mas não bateu exatamente — ex: com/sem acento)
    #    tentar comparação por similaridade simples
    def strip(s):
        return s.replace("-", "")

    for url, slug, _id in matches:
        if strip(slug) == strip(expected_slug):
            return url, "slug_strip_match"

    # 3) sem nome exato → pega o primeiro JusBrasil na ordem do Google
    return matches[0][0], "first_jusbrasil_match"


def search(name: str) -> dict:
    """Executa a busca usando web_search via subprocess e devolve o resultado."""
    import subprocess

    query = build_query(name)
    slug = slugify(name)

    # Chama o utilitário de busca. Usamos curl direto à API de pesquisa do
    # backend CASO não tenhamos integração — mas como web_search é uma tool
    # agent-side, retornamos metadados para o agente executar a busca.
    # Aqui apenas preparamos o envelope.
    return {
        "input_name": name,
        "expected_slug": slug,
        "google_query": query,
        "hint": "execute_web_search_then_filter",
    }


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "JAMILA DRIELLY MOURA OLIVEIRA"
    out = search(name)
    print(json.dumps(out, ensure_ascii=False, indent=2))
