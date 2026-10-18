---
name: sac-sessao
description: Use ao iniciar, retomar, pausar, registrar checkpoint ou encerrar uma sessão de estudo, e quando o estudante disser que vai parar, voltou depois de um tempo ou perguntar quanto estudou.
---

# Sessão: início, retomada e encerramento

## Início e retomada

1. `python3 scripts/sac.py briefing` (use `-d <slug>` se houver várias disciplinas).
2. Leia o resultado com senso crítico: o "Estado atual" é calculado das evidências. Se houver **sessão aberta anterior**, pergunte se o estudante quer encerrá-la formalmente (`sessao encerrar`) ou deixar que `sessao iniciar` a marque como abandonada.
3. Se `briefing` indicar mudanças em fontes (NOVO/ALTERADO/AUSENTE), avise e proponha reingestão (`sac-ingestao`) antes de ensinar com base nelas.
4. Abertura em poucas linhas: onde parou, o que **foi demonstrado** (não o que foi apresentado), próxima atividade sugerida, revisões vencidas, risco de cronograma se relevante. Ofereça opções naturais.
5. Ao retomar um tópico, **não recomece do início**: faça uma recuperação breve (1–3 perguntas sobre o ponto em que parou) e ajuste conforme a resposta. Registre as respostas como tentativas.
6. `python3 scripts/sac.py sessao iniciar --objetivo "..."`. Faça isso **antes** de registrar tentativas: sem sessão aberta o CLI avisa e a tentativa fica sem vínculo.

## Durante

- `sessao checkpoint --nota "..." --topico <id>` após cada atividade concluída.
- Se o estudante avisar que vai pausar: `sessao pausar` e, ao voltar, `sessao retomar`. Pausa não declarada **não** é descontada; não presuma pausas.

## Encerramento (quando o estudante indicar que vai parar)

1. Resuma o que foi estudado e separe **demonstrado** (há tentativas independentes registradas) de **apenas apresentado**.
2. Garanta que erros e dúvidas importantes estejam registrados: tentativas com `--erro`, e `pendencia add --categoria duvida --texto "..."` para dúvidas abertas.
3. Pergunte quantos minutos de estudo efetivo ele considera ter feito (opcional). Só registre o que ele disser em `--minutos-efetivos`; nunca estime.
4. `python3 scripts/sac.py sessao encerrar --resumo "..." --proximo "..." --concluida sim|parcial|nao --demonstrado "..." --topico <id>` (repita `--topico`).
   - `--concluida sim` só se o objetivo da sessão foi **demonstrado**.
5. `python3 scripts/sac.py validar`. Se houver ERRO, corrija ou reporte; se houver AVISO relevante, mencione.
6. Se o plano mudou, atualize `07_PLANEJAMENTO/plano_de_estudos.md` (arquivo manual) e diga o que mudou.
7. Apresente o **ponto exato de retomada** (a linha "Retomada" que o CLI imprime, mais seu comentário).

## Saída sem encerramento

Nada a fazer na hora. Na próxima abertura, `sessao iniciar` registra abandono: fim = último registro confiável; tempo ativo fica "desconhecido". Explique isso ao estudante se houver dúvida sobre o tempo.

## Se perguntarem "quanto estudei?"

Mostre as três grandezas separadas (relógio, timer ativo, efetivo declarado) de `estado_atual.md`. Diga que não há cronômetro automático e que o efetivo só existe se foi declarado.
