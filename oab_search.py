#!/usr/bin/env python3
"""
Buscador de OAB exata por nome + UF.

Estratégia:
1. Mapear UF (sigla do estado) → site officiel da seccional OAB.
2. Slugificar o nome para comparar com a URL/perfil.
3. Buscar no Google com filtro de site: "<nome>" site:<oab-site>.
4. Filtrar resultados cujo domínio = site da seccional e cujo path contém o slug.
5. Extrair o número OAB/<UF> dos snippets via regex robusto (cobre vários formatos).
6. Formatar canonicamente: "<UF><número>" (ex: "SP123456").

Funções públicas:
    validate_uf(uf)                 -> bool
    normalize_uf(uf)                -> "SP" | None
    slugify(name)                   -> str
    build_query(name, uf)           -> "..." (query Google pronta)
    find_oab_url(results, slug, uf) -> (url | None, match_quality)
    extract_oab_number(text, uf)    -> "123456" | None
    format_oab(number, uf)          -> "SP123456"

Match qualities (prioridade):
    1) exact_oab_profile_url   — URL da seccional cujo path bate com slug exato
    2) partial_oab_profile_url — URL da seccional com slug próximo (after strip)
    3) first_oab_site_url      — qualquer URL da seccional (último recurso)
    4) no_oab_url_in_results   — nenhuma URL da seccional veio do Google
"""
import re
import unicodedata
from urllib.parse import urlparse


# ====================================================================
# MAPA UF → SITE OFICIAL DA SECCIONAL OAB
# ====================================================================

OAB_SITES = {
    "AC": "oabac.org.br",
    "AL": "oab-al.org.br",
    "AM": "oabam.org.br",
    "AP": "oabap.org.br",
    "BA": "oab-ba.org.br",
    "CE": "oabce.org.br",
    "DF": "oabdf.org.br",
    "ES": "oabes.org.br",
    "GO": "oabgo.org.br",
    "MA": "oabma.org.br",
    "MG": "oabmg.org.br",
    "MS": "oabms.org.br",
    "MT": "oabmt.org.br",
    "PA": "oabpa.org.br",
    "PB": "oabpb.org.br",
    "PE": "oabpe.org.br",
    "PI": "oabpi.org.br",
    "PR": "oabpr.org.br",
    "RJ": "oabrj.org.br",
    "RN": "oabrn.org.br",
    "RO": "oabro.org.br",
    "RR": "oabrr.org.br",
    "RS": "oabrs.org.br",
    "SC": "oabsc.org.br",
    "SE": "oab-se.org.br",
    "SP": "oabsp.org.br",
    "TO": "oabto.org.br",
}

UF_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
    "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina",
    "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins",
}

# Após slugify (lowercase + sem acento + hífens). Cobre com/sem acento.
_UF_NAME_KEYS = {
    "acre": "AC", "alagoas": "AL", "amazonas": "AM", "amapa": "AP",
    "bahia": "BA", "ceara": "CE", "distrito-federal": "DF", "espirito-santo": "ES",
    "goias": "GO", "maranhao": "MA", "minas-gerais": "MG", "mato-grosso-do-sul": "MS",
    "mato-grosso": "MT", "para": "PA", "paraiba": "PB", "pernambuco": "PE",
    "piaui": "PI", "parana": "PR", "rio-de-janeiro": "RJ", "rio-grande-do-norte": "RN",
    "rondonia": "RO", "roraima": "RR", "rio-grande-do-sul": "RS", "santa-catarina": "SC",
    "sergipe": "SE", "sao-paulo": "SP", "tocantins": "TO",
}


# ====================================================================
# VALIDAÇÃO / NORMALIZAÇÃO DE UF
# ====================================================================

def validate_uf(uf: str) -> bool:
    """True se `uf` é uma UF brasileira válida (sigla ou nome). Case-insensitive."""
    return normalize_uf(uf) is not None


def normalize_uf(uf: str) -> str | None:
    """Aceita 'sp', 'SP', 'São Paulo', 'sao paulo' → 'SP'. Retorna None se inválida."""
    if not uf:
        return None
    raw = uf.strip()
    if not raw:
        return None
    up = raw.upper()
    if up in OAB_SITES:
        return up
    # Nome completo: slugify (lowercase + sem acento + hífens).
    key = slugify(raw)
    if key in _UF_NAME_KEYS:
        return _UF_NAME_KEYS[key]
    # Tentativa com espaços: "sao paulo" usado em comentários humanos.
    key_with_spaces = re.sub(r"-", " ", key)
    if key_with_spaces in _UF_NAME_KEYS:
        return _UF_NAME_KEYS[key_with_spaces]
    return None


# ====================================================================
# SLUGIFY (mesmo algoritmo do JusBrasil para consistência)
# ====================================================================

def slugify(name: str) -> str:
    """Lowercase + sem acento + hífens. Ex: 'João da Silva' -> 'joao-da-silva'."""
    nfkd = unicodedata.normalize("NFKD", name)
    only_ascii = "".join(c for c in nfkd if not unicodedata.combining(c))
    only_ascii = only_ascii.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", only_ascii).strip("-").lower()
    return cleaned


# ====================================================================
# QUERY GOOGLE
# ====================================================================

def build_query(name: str, uf: str) -> str:
    """Constrói a query: nome entre aspas + site da seccional + uf explícito."""
    if uf.upper() not in OAB_SITES:
        raise ValueError(f"UF inválida: {uf!r}")
    quoted = f'"{name.strip()}"'
    site = OAB_SITES[uf.upper()]
    return f"{quoted} site:{site} {uf.upper()}"


# ====================================================================
# FILTRO DE URL
# ====================================================================

def _is_on_oab_site(url: str, site: str) -> bool:
    """True se `url` pertence ao domínio do site da seccional (incluindo www.*)."""
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return False
    base = site.lower()
    return base in netloc or ("www." + base) in netloc


def find_oab_url(results: list, expected_slug: str, uf: str) -> tuple[str | None, str]:
    """
    Filtra e ranqea URLs da seccional OAB do estado `uf`.

    `results` é uma lista de dicts {url, title, description}.
    Retorna (url, match_quality) onde match_quality ∈ {
        'exact_oab_profile_url',
        'partial_oab_profile_url',
        'first_oab_site_url',
        'no_oab_url_in_results',
    }
    """
    if uf.upper() not in OAB_SITES:
        return None, "no_oab_url_in_results"
    site = OAB_SITES[uf.upper()]
    candidates = []
    for r in results:
        url = r.get("url") or r.get("link") or ""
        if not _is_on_oab_site(url, site):
            continue
        path_slug = slugify(urlparse(url).path)
        candidates.append((url, path_slug))

    if not candidates:
        return None, "no_oab_url_in_results"

    # 1) Exact match: slug_in_path == expected_slug, OU expected_slug é substring do path_slug.
    for url, slug_in_path in candidates:
        if slug_in_path == expected_slug:
            return url, "exact_oab_profile_url"
        if expected_slug and expected_slug in slug_in_path:
            return url, "exact_oab_profile_url"

    # 2) Partial: bate após remover hifens (variação de acento).
    def strip(s):
        return s.replace("-", "")

    for url, slug_in_path in candidates:
        if strip(slug_in_path) == strip(expected_slug):
            return url, "partial_oab_profile_url"
        if strip(expected_slug) and strip(expected_slug) in strip(slug_in_path):
            return url, "partial_oab_profile_url"

    # 3) Qualquer URL da seccional.
    return candidates[0][0], "first_oab_site_url"


# ====================================================================
# EXTRAÇÃO DO NÚMERO OAB
# ====================================================================
# Regex robusto. Casa:
#   "OAB/SP 123.456"     OAB + UF + espaço + nnn.nnn
#   "OAB n° SP 123456"   OAB + indicador + UF + número
#   "OAB-SP-123456"      OAB + UF + hífen + número
#   "SP 123.456"         UF + espaço + nnn.nnn
#   "SP123456"           UF + número grudad
#   "SP-123456"          UF + hífen + número
#
# NÃO casa (proteção via lookahead):
#   "Processo SP 123456-78.1234 5.01.0001" (formato CNJ)
#   "em MG 99999" com UF=SP (UF mismatch — o pattern é gerado com UF literal)
# ====================================================================

_OAB_RE_CACHE = {}


def _oab_pattern(uf: str) -> re.Pattern:
    uf_up = uf.upper()
    if uf_up in _OAB_RE_CACHE:
        return _OAB_RE_CACHE[uf_up]
    pat = re.compile(
        rf"(?<!\d)(?:OAB\s*[/n°\-.]?\s*)?\b{re.escape(uf_up)}\s*[-/]?\s*"
        rf"(\d{{3,7}}(?:[.,]\d{{3}})*)(?![\d\-])",
        re.IGNORECASE,
    )
    _OAB_RE_CACHE[uf_up] = pat
    return pat


def extract_oab_number(text: str, uf: str) -> str | None:
    """
    Procura o número OAB/<UF> em `text`. Retorna string só com dígitos ou None.

    Casa (UF='SP'):
        "OAB/SP 123.456"            -> "123456"
        "Inscrição: SP-123456"      -> "123456"
        "OAB n° SP 123456"          -> "123456"
        "SP123456"                  -> "123456"

    NÃO casa:
        "Processo SP 123456-78.1234 …" (CNJ; excluído via lookahead)
        "em MG 99999" quando UF='SP' (UF mismatch — UF literal no regex)
    """
    if not text:
        return None
    if uf.upper() not in OAB_SITES:
        return None
    matches = _oab_pattern(uf).findall(text)
    if not matches:
        return None
    # Limpa separadores visuais (`.` ou `,` a cada 3 dígitos).
    cleaned = [re.sub(r"[^\d]", "", m) for m in matches]
    cleaned = [m for m in cleaned if 3 <= len(m) <= 7]
    if not cleaned:
        return None
    return min(cleaned, key=len)


# ====================================================================
# FORMATO CANÔNICO
# ====================================================================

def format_oab(number: str, uf: str) -> str:
    """Retorna formato canônico '<UF><número>'. Ex: format_oab('123456', 'SP') -> 'SP123456'."""
    return f"{uf.upper()}{number}"
