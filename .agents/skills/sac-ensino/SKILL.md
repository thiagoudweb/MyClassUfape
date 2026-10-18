---
name: sac-ensino
description: Use quando o estudante pedir para aprender, entender ou ser ensinado sobre um tópico, ao iniciar um tópico novo (diagnóstico), ou quando precisar de analogias, exemplos resolvidos e progressão de dificuldade.
---

# Ensinar

Consulte `disciplinas/<slug>/03_CONHECIMENTO`, as fontes registradas e o estado do tópico (`04_MEMORIA_DO_ALUNO/dominio_por_topico.md`) antes de explicar. Cite a fonte usada (arquivo e seção/página **verificada**). Conteúdo que não vem dos materiais deve ser sinalizado como externo ou conhecimento geral.

## Diagnóstico (tópico novo)
Poucas perguntas, bem escolhidas: o que já sabe, pré-requisitos, concepções equivocadas, nível adequado, objetivo concreto da sessão. Registre as respostas como tentativas (`recuperacao`). Silêncio ou ausência de histórico **não** são prova de desconhecimento. Se há pré-requisito frágil (ver `dificuldades_recorrentes.md`), proponha corrigi-lo antes.

## Progressão
1. Conhecimento prévio. 2. Conceito central. 3. Analogia concreta. 4. Onde a analogia funciona e onde falha. 5. Exemplo resolvido. 6. Exemplo com participação do estudante. 7. Resolução independente. 8. Questão de transferência. 9. Correção dos erros. 10. Registro e revisão.

Adapte a teoria, cálculo, história ou argumentação. Explique em camadas: intuição, definição formal, mecanismo, exemplo real, limites e exceções, aplicação em situação nova. Analogia serve a **um mecanismo específico**; sem decoração e sem introduzir erro conceitual. Retire as pistas gradualmente e inclua problemas difíceis e de transferência, não só fáceis.

## Recuperação ativa
Ao retomar algo já visto, peça primeiro que o estudante tente recuperar sem consultar. Depois dê feedback. Se errar, investigue a causa provável antes de entregar a solução, e trate a causa como **hipótese**.

## Registro (obrigatório para contar como progresso)
Cada tentativa do estudante, logo após a correção:
`python3 scripts/sac.py tentativa --topico <id> --questao Q0001 --tipo reconhecimento|recuperacao|explicacao|aplicacao|transferencia --pontuacao 0..1 [--confianca 1-5] [--erro <tipo>] [--com-ajuda] --nota "..."`
Pontue pela rubrica em `06_AVALIACOES/rubricas_de_correcao.md`. Reconhecimento e tentativas com ajuda **não** contam como recuperação independente. Cadastre a pergunta antes (`questao add`, skill `sac-avaliacao`) e cite `--questao`: tentativa sem questão cadastrada não conta como "questão distinta" para o domínio, e o CLI avisa. Mantenha a sessão aberta (`sessao iniciar`) para o registro entrar no tempo e nos tópicos da sessão. Peça a confiança (1–5) em algumas tentativas, pois a divergência confiança×desempenho é informativa.

Ao final do bloco, olhe a saída do CLI: ela mostra o estado calculado e a próxima revisão. Informe ao estudante em linguagem simples, sem prometer domínio que o CLI não atribuiu.
