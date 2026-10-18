---
name: sac-materiais
description: Use quando o estudante pedir resumo, mapa mental, esquema, tabela comparativa, flashcards, lista de exercícios ou guia de revisão, ou quando for preciso pesquisar fontes externas para aprofundar um tópico.
---

# Materiais de estudo e pesquisa externa

Gere o formato que serve ao objetivo pedagógico, não todos por padrão. Salve o que for durável em `03_CONHECIMENTO/topicos/<id>.md` e registre no `03_CONHECIMENTO/indice_de_conteudos.md` (arquivos manuais, sem resumos extensos no estado global). Todo material cita as fontes (arquivo e seção/página verificada) e rotula o que é externo.

- **Resumo:** conceitos essenciais, relações causais, definições, exemplos, exceções, referências. É síntese, não transcrição; preserve a precisão técnica.
- **Mapa mental:** conceito central, ramos, subtemas, conexões. Entregue versão em Markdown aninhado e, se útil, em Mermaid. Não vire lista de parágrafos.
- **Esquemas e tabelas:** processos, classificações, diferenças entre conceitos, fórmulas e sequências.
- **Flashcards:** uma unidade de conhecimento por cartão, resposta verificável, contexto suficiente; sem cartões vagos ou longos. Ao usá-los, registre como tentativas (`recuperacao`) para entrarem na revisão.
- **Listas de exercícios:** por objetivo, pré-requisito e dificuldade, com solução comentada e critérios. Cadastre as questões (`sac-avaliacao`) para aplicá-las com rastreio.
- **Guia de revisão:** priorize o frágil, o esquecido e o próximo de ser cobrado (use `sac.py revisoes` e `dificuldades_recorrentes.md`); não reapresente tudo igualmente.

Material **não** vira evidência de domínio: gerar ou ler um resumo não altera estado. Só tentativas alteram.

## Pesquisa externa
Quando houver valor real: conceito mal explicado nos materiais, informação possivelmente desatualizada, divergência entre fontes, exemplos concretos, aprofundamento. Priorize artigos e revisões, livros acadêmicos, documentação oficial, instituições de pesquisa e fontes primárias. Registre título, autoria, data, publicação/instituição, link e **a afirmação que a fonte sustenta**. Diferencie "exigido pela disciplina" de "aprofundamento opcional". Em conflito com o material didático, explique a diferença e registre `pendencia add --categoria conflito`. Não cite o que não foi efetivamente acessado.
