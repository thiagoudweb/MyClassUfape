---
name: sac-guia
description: Use no início de toda conversa, quando o estudante disser "oi", "menu", "ajuda", "e agora?", "não sei o que fazer", ou depois de concluir qualquer ação, para oferecer opções clicáveis em vez de pedir comandos.
---

# Guia e menus: o estudante não decora comandos

## Princípio
O estudante nunca deve precisar digitar ou lembrar um comando. Você roda os comandos; ele **escolhe**.

## Passos
1. Rode `python3 scripts/sac.py guia --json` (com `-d <slug>` se houver várias disciplinas). O resultado traz `opcoes` (prioritárias, já ordenadas), `sempre` (sempre disponíveis), `resumo` e `topicos`.
2. Apresente as `opcoes` como **escolhas**:
   - Se a sua interface tiver ferramenta de pergunta com botões ou opções (por exemplo, perguntas de múltipla escolha), use-a: de 2 a 4 opções, rótulos curtos, a recomendada primeiro.
   - Se não tiver, mostre uma **lista numerada** e peça que ele responda só com o número.
   - Antes das opções, escreva 1 ou 2 frases de contexto (ex.: "Você tem 2 revisões vencidas e uma prova em 9 dias.").
3. Quando ele escolher, **execute** (cada opção tem `acao`, `dizer` e `comando`). Se faltar um dado (objetivo da sessão, data, origem da data), pergunte **uma coisa por vez**, também com opções quando possível.
4. Depois de cada ação, ofereça de 2 a 3 próximos passos como nova escolha. Não deixe o estudante sem saber o que fazer.
5. Mostre o **comando equivalente** em uma linha curta (ex.: "Se quiser rodar sozinho: `python3 scripts/sac.py risco`"), mas só quando ajudar. Nunca exija que ele o digite.
6. Se ele preferir botões visuais, lembre que existe o painel: dê duplo clique em `Abrir-Painel.bat` (Windows) ou `Abrir-Painel.command` (macOS), ou rode `python3 scripts/sac.py painel`.

## Durante o estudo
- Questões de múltipla escolha: apresente as alternativas como opções clicáveis. Lembre que tipo `reconhecimento` não conta como recuperação independente.
- Quando pedir uma explicação ou resolução, é resposta livre: não use opções (a escolha entre alternativas é outro tipo de evidência).
- Ao encerrar, ofereça: "Encerrar agora", "Mais uma questão", "Revisar um ponto fraco".

## Proibido
- Pedir ao estudante que digite um comando que você mesmo pode rodar.
- Inventar opções que o guia não trouxe e que você não consiga executar.
- Esconder o resultado de um comando: se deu `ERRO` ou `FALHA DE GRAVAÇÃO`, diga com clareza o que aconteceu e se algo foi ou não salvo.
