---
name: sac-revisao
description: Use quando houver revisões vencidas, quando o estudante pedir revisão, "o que devo revisar hoje", revisão dos pontos fracos, ou intercalação de tópicos.
---

# Revisão espaçada

## O que é do código e o que é seu
O **código** agenda: escada de intervalos em `config.json` (padrão 1, 3, 7, 14, 30, 60 dias), avanço só quando a revisão está devida e a recuperação foi independente e ≥ limiar; erro volta ao início; antes de prova, a revisão é antecipada (margem configurável). **Você nunca altera datas de revisão à mão.** Você conduz a revisão e informa a pontuação honesta.

## Fluxo
1. `python3 scripts/sac.py revisoes` mostra a fila (vencidas primeiro, tópicos críticos em empate).
2. Para cada tópico escolhido, **recuperação ativa antes de qualquer reexplicação**: pergunta aberta, explicação com palavras próprias, reconstrução de processo, problema novo. Use questões já cadastradas ou crie novas (skill `sac-avaliacao`); prefira questões diferentes das usadas antes.
3. Registre cada resposta com `sac.py tentativa` (`recuperacao`, `explicacao`, `aplicacao` ou `transferencia`). **Reconhecimento acertado não equivale a lembrar**: use-o só como apoio, e ele não avança a escada.
4. Só depois da tentativa dê feedback e, se preciso, reexplique o trecho falho.
5. Informe ao estudante a nova data (vem na saída do CLI) e por quê, em uma frase.

## Priorização
Ordem sugerida: vencidas de tópicos críticos, vencidas gerais, tópicos com `revisao_necessaria`, pré-requisitos frágeis de tópicos em andamento, e por fim as que vencem nos próximos dias. Se o estudante tem pouco tempo, escolha 1 a 3 tópicos e diga o que ficou para depois. Não obrigue revisar tudo no início da sessão.

## Intercalação
Quando houver base mínima em tópicos relacionados, misture questões de procedimentos que podem ser confundidos, para treinar a **escolha** da estratégia. Não intercale enquanto o conceito fundamental ainda não foi compreendido.

## Atenção
- Confiança alta com erro (veja `dificuldades_recorrentes.md`) merece revisão mais cedo e uma conversa sobre calibração, sem julgamento.
- Se o estudante pedir para "marcar como revisado" sem tentativa: explique que sem recuperação registrada o tópico não avança, e ofereça uma revisão curta.
