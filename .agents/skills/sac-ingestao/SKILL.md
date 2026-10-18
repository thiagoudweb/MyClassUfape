---
name: sac-ingestao
description: Use quando o estudante entregar novos materiais (PDFs, ementa, slides, listas, provas, bibliografia), ao configurar uma disciplina nova, ou quando o briefing apontar fontes novas, alteradas ou ausentes.
---

# Ingestão de materiais

Antes de ensinar com base em um material, ele precisa ter sido ingerido. Disciplina nova: `python3 scripts/sac.py nova <slug> --nome "..." --objetivo "..."` e coloque os arquivos em `disciplinas/<slug>/01_FONTES/`.

## 1. Inventário
`python3 scripts/sac.py fonte verificar` lista o que é novo, alterado ou ausente. Anote duplicatas, versões, tipo (ementa, livro, slides, lista, prova) e problemas (páginas ausentes, digitalização que exige OCR). **Não presuma que um PDF foi lido por inteiro** só porque existe.

## 2. Extração e validação
Extraia o texto (`pdftotext`, ou o recurso de leitura de PDF disponível). Para tabelas, fórmulas, figuras e páginas escaneadas, use leitura visual ou peça uma versão melhor. Registre limitações que afetem a interpretação.

## 3. Manifesto
Para cada arquivo: `python3 scripts/sac.py fonte registrar 01_FONTES/<arquivo> --tipo "..." --assuntos "..." --nota "limitações"`. O CLI calcula hash e **verifica o número de páginas** de PDFs; para outros formatos fica "desconhecido". Nunca escreva páginas ou referências que você não conferiu. Reregistrar um arquivo alterado cria nova versão.

## 4. Mapeamento conceitual
Extraia tópicos, subtópicos, definições, fórmulas, exemplos, exercícios e relações. Cadastre cada tópico:
`python3 scripts/sac.py topico add <id> --nome "..." --prereq <id> --fonte "F001 p.12-30 (confirmado)" [--critico] [--previsto-ate AAAA-MM-DD --previsto-origem oficial|confirmada_estudante|estimada]`
- Cadastre pré-requisitos antes dos dependentes.
- `--critico` só para tópicos que a disciplina ou o estudante marcarem como essenciais; diga ao estudante o critério usado.
- `--fonte` precisa apontar para algo que você viu.
Mantenha também `02_MAPA_DA_DISCIPLINA/{ementa,mapa_conceitual,pre_requisitos}.md` (manuais), com árvore de tópicos e dependências.

## 5. Vinculação à ementa
Classifique cada item: correspondência explícita, provável, complementar, não localizada, divergência. Divergências e lacunas: `pendencia add --categoria fonte|conflito --texto "..."`. **Não declare a disciplina coberta** antes de conferir todos os itens da ementa.

## 6. Datas
Cada data oficial: `python3 scripts/sac.py data --titulo "AB1" --data AAAA-MM-DD --origem oficial|confirmada_estudante|estimada|desconhecida --tipo prova|entrega|outro --fonte "..."`. Sem data no material, não invente: peça ao estudante.

## 7. Validação e relatório
Confira amostras (fórmulas, definições, datas, tabelas relevantes para prova) contra o original. Rode `python3 scripts/sac.py validar`. Entregue o **relatório de ingestão**: arquivos processados, tópicos identificados, cobertura estimada da ementa (como estimativa), problemas de leitura, conflitos, pendências e próximos passos. Aponte o que foi apenas estimado.
