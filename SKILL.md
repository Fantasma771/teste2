# Buscador de Processos JusBrasil por Nome (com OAB por Estado)

## Goal
Receber o nome completo de uma pessoa (e, opcionalmente, a sigla do estado — UF) e devolver:
1. A URL canônica do JusBrasil (`/processos/nome/{id}/{slug}`) que lista todos os processos encontrados para esse nome.
2. Quando o UF é fornecido, o **número OAB exato** desse nome naquela seccional, com URL de referência do site da seccional.

Nada é chutado: tanto a URL JusBrasil quanto o número OAB vêm diretamente de resultados reais do Google.

## Inputs
- `nome` (string, **required**): nome completo da pessoa. Qualquer capitalização ou acento é aceito.
- `uf` (string, **optional**): sigla do estado brasileiro para a consulta de OAB. Aceita sigla (`SP`) ou nome (`São Paulo`). UFs válidas: AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP, TO.

## Strategy — JusBrasil (sempre rodado)
JusBrasil endereça a página agregada de uma pessoa como `/processos/nome/{numeric_id}/{slug}` onde o slug é `lowercase-com-hifens-sem-acento`. Uma busca em Google `"<nome>" site:jusbrasil.com.br processos` tipicamente retorna essa página entre os primeiros resultados. Filtros em ordem:
1. **exact_slug_match** — slug da URL bate exatamente com o slug do nome.
2. **slug_strip_match** — slug bate após remover hifens (cobre variações de acento/separador).
3. **first_jusbrasil_match** — primeira URL JusBrasil de processos na ordem do Google (último recurso).
4. **no_jusbrasil_url_in_results** — nenhuma URL JusBrasil encontrada.

## Strategy — OAB exata (somente se `uf` for fornecido)
Para evitar OAB errada, restringimos o estado por seção OAB. Cada UF tem site oficial próprio:
`SP → oabsp.org.br`, `RJ → oabrj.org.br`, `MG → oabmg.org.br`, ..., `DF → oabdf.org.br` (mapa em `oab_search.py:OAB_SITES`).

Query: `"<nome>" site:<oab-site> <UF>` → melhor resultado na ordem:
1. **exact_oab_profile_url** — URL da seccional cujo path contém o slug exato do nome.
2. **partial_oab_profile_url** — URL da seccional cujo path bate com o slug após `replace("-","")`.
3. **first_oab_site_url** — qualquer URL da seccional (último recurso).
4. **no_oab_url_in_results** — nenhuma URL da seccional veio do Google.

O **número OAB** é extraído do `title + description` via regex robusto em `oab_search.py:extract_oab_number` (cobre formatos `OAB/SP 123.456`, `SP-123456`, `SP123456`, `OAB n° SP 123456`). Saída canônica: `<UF><número>` (ex: `SP123456`).

## Procedure

### Step 1 — Localizar os scripts
```bash
cat /home/user/agent/app-files.json
```
Os arquivos `jusbrasil_search.py` e `oab_search.py` ficam no diretório indicado em `path`. Use o campo `path` literal.

### Step 2 — Slugify + montar query JusBrasil
```bash
python3 -c "
import sys, json
sys.path.insert(0, '<SCRIPT_DIR>')
from jusbrasil_search import slugify, build_query
nome = '<NOME>'
print(json.dumps({'slug': slugify(nome), 'query': build_query(nome)}))
"
```

### Step 3 — Buscar no Google (JusBrasil)
Use `web_search` com a query do Step 2 e `count`=10.

### Step 4 — Filtrar/rankear URL JusBrasil + extrair total de processos
```bash
python3 -c "
import sys, json, re
sys.path.insert(0, '<SCRIPT_DIR>')
from jusbrasil_search import slugify, find_jusbrasil_url
data = json.loads(sys.stdin.read())
url, reason = find_jusbrasil_url(data['results'], data['slug'])
snippets = ' '.join(r.get('description','') for r in data['results'])
m = re.search(r'encontrou\s+(\d+)\s+processos?', snippets)
print(json.dumps({
    'jusbrasil_url': url,
    'match_quality': reason,
    'total_processos': int(m.group(1)) if m else None,
    'slug_calculado': data['slug'],
}))
" <<< '<JSON com slug + results>'
```

### Step 5 — (opcional) OAB lookup quando `uf` é fornecido

**5a — Validar/normalizar UF + montar query**
```bash
python3 -c "
import sys, json
sys.path.insert(0, '<SCRIPT_DIR>')
from oab_search import normalize_uf, build_query
uf = '<UF_INPUT>'
uf_norm = normalize_uf(uf)
if not uf_norm:
    print(json.dumps({'error': f'UF inválida: {uf!r}. Válidas: ' + ','.join(sorted(__import__(\"oab_search\").OAB_SITES))}))
    sys.exit(0)
print(json.dumps({'uf': uf_norm, 'query': build_query('<NOME>', uf_norm)}))
"
```

**5b — Buscar no Google**
Use `web_search` com a query=`q` do passo 5a, `count`=10.

**5c — Filtrar URL da seccional + extrair número OAB**
```bash
python3 -c "
import sys, json, re
from urllib.parse import urlparse
sys.path.insert(0, '<SCRIPT_DIR>')
from oab_search import slugify, find_oab_url, extract_oab_number, format_oab
data = json.loads(sys.stdin.read())
url, quality = find_oab_url(data['results'], slugify(data['nome']), data['uf'])
blob = ' '.join((r.get('title','') + ' ' + r.get('description','')) for r in data['results'])
num = extract_oab_number(blob, data['uf'])
oab_fmt = format_oab(num, data['uf']) if num else None
print(json.dumps({
    'uf': data['uf'],
    'oab_numero': num,
    'oab_formatado': oab_fmt,
    'oab_url': url,
    'oab_match_quality': quality,
}))
" <<< '<JSON com nome, uf, results>'
```

### Step 6 — Montar a resposta ao usuário (pt-BR)
- URL canônica JusBrasil (sempre).
- Total de processos (se extraído do snippet).
- `match_quality` JusBrasil apenas se ≠ `exact_slug_match`.
- Bloco OAB (somente se `uf` foi fornecido):
  - `oab_formatado` (ex: `SP123456`) + `oab_url` da seccional.
  - `oab_match_quality` se ≠ `exact_oab_profile_url` ou se o número não foi extraído.
- Em caso de `no_oab_url_in_results` ou `no_oab_number_in_results`: diga claramente que não foi possível confirmar a OAB nessa seccional.

## Important rules
- **Nunca invente** a URL JusBrasil nem o número OAB — ambos precisam vir de resultados reais do `web_search`.
- **Não tente validar** a URL fazendo GET no JusBrasil ou na seccional (ambos retornam 403 para bots); o Google já validou ao retorná-la.
- **Não encadeie** a OAB com a JusBrasil — rode as duas buscas independentemente, cada qual com seu próprio filtro `site:`.
- O mapa `OAB_SITES` é a fonte de verdade para a seccional. Não invente domínio fora dele.
- Cite o slug calculado do nome e a UF normalizada na resposta final para o usuário auditar.

## Failure modes (JusBrasil)
- `no_jusbrasil_url_in_results` → "JusBrasil não tem página agregada para `<nome>`. Tente variações ou outra pessoa."
- `slug_strip_match` → "Slug bateu após remover hifens. Abra a URL para confirmar."
- `first_jusbrasil_match` → "Mais de uma pessoa com esse nome; veja a primeira, mas reveja se é a certa."

## Failure modes (OAB)
- `invalid_uf` → "UF fornecida (`<X>`) não é válida. Use siglas como SP, RJ, MG…"
- `no_oab_url_in_results` → "A seccional `<oab site>` não retornou uma página com o nome `<nome>` no Google. Não foi possível confirmar a OAB."
- `no_oab_number_in_results` → "Encontrei uma página na seccional, mas o número OAB/<UF> não veio no snippet. Confirme manualmente."
- `first_oab_site_url` → "A seccional retornou páginas mas nenhuma com slug exato. Pode ser a pessoa certa ou não — confirme o número."
- Múltiplos números OAB distintos no snippet → sinalize ambiguidade e liste os candidatos.

## Output shape
```json
{
  "nome": "Juliana Carvalho Gomes",
  "uf": "MG",
  "slug_jusbrasil": "juliana-carvalho-gomes",
  "jusbrasil_url": "https://www.jusbrasil.com.br/processos/nome/...",
  "jusbrasil_match_quality": "exact_slug_match",
  "total_processos": 290,
  "oab_url": "https://www.oabmg.org.br/...",
  "oab_numero": "123456",
  "oab_formatado": "MG123456",
  "oab_match_quality": "exact_oab_profile_url"
}
```
