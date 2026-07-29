# 🌐 Buscador JusBrasil por Nome — Site self-hosted

Arquivo único: **`jusbrasil-website.html`**

Contém TODO o sistema do agente "Buscador de Processos JusBrasil por Nome" empacotado como um site HTML standalone. Zero backend, zero dependências além do Tailwind via CDN.

## 🚀 Como usar

| Opção | Comando |
|---|---|
| **Local (mais rápido)** | Duplo clique em `jusbrasil-website.html` |
| **GitHub Pages** | Suba o arquivo, ative Pages → main / |
| **Netlify Drop** | Arraste o `.html` em https://app.netlify.com/drop |
| **Vercel** | `vercel deploy` na pasta |
| **S3 / Cloudflare Pages** | Upload → pronto |

Funciona offline depois de carregado (não envia nada do navegador).

## 🔁 Lógica embutida (idêntica ao agente CREAO)

| Função | O que faz |
|---|---|
| `slugify(name)` | lowercase + remove acento + hífens |
| `buildQuery(name)` | `"<nome>" site:jusbrasil.com.br processos` |
| `findJusbrasilUrl(results, slug)` | `exact_slug_match` → `slug_strip_match` → `first_jusbrasil_match` → `no_jusbrasil_url_in_results` |
| `extractTotal(results)` | regex `encontrou\s+(\d+)\s+processos?` |

## 📌 Caso demonstrativo

Pré-carregado com o último caso real que você rodou:

> **Juliana Carvalho Gomes** → `https://www.jusbrasil.com.br/processos/nome/28555609/juliana-carvalho-gomes` — `exact_slug_match` — **290 processos** (TJMG · TJDFT).

## ⚠️ Nota sobre busca ao vivo

O Google bloqueia chamadas client-side por CORS. Para a **busca real ao vivo**, continue usando o agente CREAO no chat:

> Rode o agente `Buscador de Processos JusBrasil por Nome` com `nome=<pessoa>`.

O site serve como **interface self-hosted, documentação e demonstrador** do pipeline completo.

## 🧪 Customização

- Troque o caso pré-carregado em `SAMPLE` no `<script>` final.
- Edite a paleta no `<style>` (busca por `gradient-bg` / cores Tailwind).
- Adicione mais nomes hardcoded em `sampleFor()` se quiser biblioteca de casos.
