---
name: sac-avaliacao
description: Use para criar ou aplicar quiz, diagnóstico, exercícios ou simulado, para corrigir respostas do estudante e para registrar tentativas e erros.
---

# Avaliação, quiz e correção

## Criar questões
Cada questão é cadastrada **antes** de ser aplicada, para ter ID, gabarito e critérios rastreáveis:
`python3 scripts/sac.py questao add --topico <id> --formato <fmt> --dificuldade 1-5 --objetivo "..." --enunciado "..." --gabarito "..." --criterios "..." --raciocinio "..." [--fonte "F001 p.12"] [--erros-alvo "confusão X/Y"]`
Formatos: multipla_escolha, resposta_curta, explicacao, verdadeiro_falso, associacao, problema, caso, corrigir_erro, cumulativa, transferencia. Varie formatos; inclua pelo menos uma tarefa de explicação ou aplicação por tópico antes de esperar domínio.

Qualidade: enunciado inequívoco; gabarito coerente com o enunciado; critérios explícitos; distratores que refletem equívocos **plausíveis**, não ambiguidade artificial; nível adequado; fonte quando houver. Confira você mesmo gabaritos numéricos (execute o cálculo) antes de cadastrar. Sem `--fonte`, a questão fica rotulada como conhecimento geral. Para questão com problema, use outro ID em vez de sobrescrever (o CLI recusa IDs repetidos).

Não use a mesma questão repetidamente como única evidência: o CLI exige pelo menos duas questões distintas na janela de domínio.

## Aplicar
- Uma pergunta por vez quando isso ajudar o diagnóstico: `python3 scripts/sac.py questao ver <ID>`.
- **Não mostre o gabarito** nem insinue a resposta antes da tentativa. `questao gabarito <ID>` só depois.
- Deixe o estudante explicar o raciocínio. Se errar, investigue a causa antes de entregar a solução.
- Simulado/cumulativo: combine tópicos antigos e novos com questões **inéditas**; diferencie desempenho imediato de retenção após intervalo.

## Corrigir e registrar
Pontue de 0 a 1 pela rubrica. Registre imediatamente:
`python3 scripts/sac.py tentativa --topico <id> --questao <ID> --tipo <tipo> --pontuacao <x> [--confianca n] [--erro <tipo>] [--com-ajuda] --resposta "<resposta do aluno>" --nota "<hipótese de causa, rotulada como hipótese>"`

Tipos de erro aceitos: lacuna_conceitual, confusao_conceitos, erro_procedimento, erro_calculo, interpretacao_incorreta, esquecimento, aplicacao_inadequada, justificativa_insuficiente. Use "justificativa_insuficiente" para resposta certa mal justificada (pontuação < 1).

Tipo da tentativa: `reconhecimento` (escolher/identificar), `recuperacao` (lembrar sem pistas), `explicacao`, `aplicacao`, `transferencia` (problema novo). Não atribua causa psicológica como fato com base em uma resposta.

## Depois da correção
Dê feedback que explique **como corrigir**. Para erros relevantes, proponha um exercício de recuperação e, se o estudante refizer, registre uma nova tentativa (o histórico nunca é apagado). Veja no retorno do CLI o novo estado e a próxima revisão. Se os resultados forem contraditórios, o estado fica conservador: proponha avaliação complementar.
