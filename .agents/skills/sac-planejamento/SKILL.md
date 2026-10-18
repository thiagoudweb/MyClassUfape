---
name: sac-planejamento
description: Use para montar ou ajustar plano de estudos, cronograma, metas semanais, avaliar atraso ou risco acadêmico, ou quando o estudante informar nova restrição de tempo ou nova data de prova.
---

# Planejamento adaptativo e cronograma

## Insumos (use só o que existe)
Datas e origem (`02_MAPA_DA_DISCIPLINA/calendario_academico.md`), prazos por tópico (`--previsto-ate`), tempo semanal informado pelo estudante (`00_ORIENTACAO/preferencias_de_estudo.md`), estados de domínio, revisões e tentativas. **Sem calendário, não invente datas**: peça ao estudante ou monte um plano **provisório**, rotulado como estimativa e baseado na disponibilidade dele.

## Registrar datas e prazos
- `sac.py data --titulo ... --data AAAA-MM-DD --origem oficial|confirmada_estudante|estimada|desconhecida [--tipo prova|entrega|outro]`.
- Prazo de tópico: `sac.py topico add <id> --previsto-ate AAAA-MM-DD --previsto-origem ...` (reaplicar atualiza).
- Alterar data **oficial** exige autorização do estudante.
- Prova com origem diferente de `desconhecida` limita automaticamente as datas de revisão.

## Risco de cronograma
`python3 scripts/sac.py risco` aplica regras explícitas (ver `07_PLANEJAMENTO/analise_de_cronograma.md`): sob controle, atenção necessária, atraso provável, atraso confirmado, indeterminado. Mostre a **evidência**. Tópico cujo prazo ainda não venceu **não** é atraso, mesmo não dominado. Tópico "não avaliado" é ausência de dado, não atraso: se estiver vencido, proponha diagnóstico em vez de acusar. `nao_iniciado` é uma declaração do estudante (`sac.py topico marcar <id> --estado nao_iniciado`).

Esse cálculo é uma heurística de base. Se a situação real divergir, diga e registre `pendencia add --categoria operacional`.

## Reorganizar
Priorize: pré-requisitos, tópicos críticos e de maior peso, provas próximas, risco de esquecimento (revisões vencidas). Estime a carga em horas e confronte com o tempo semanal informado; **não prometa recuperar um atraso sem essa conta**. Reserve margem de segurança para revisão e prova. Evite planejar minuto a minuto.

Divida objetivos grandes em entregas observáveis ("resolver 5 problemas de transferência de limites com ≥ 80%"). Atualize à mão `07_PLANEJAMENTO/plano_de_estudos.md` e `metas_semanais.md` (não são gerados) e registre a origem de cada data e de cada premissa.

## Revisão semanal
Compare plano e execução (sessões, tentativas, revisões em dia) sem culpabilizar. Rode `sac.py relatorio` e proponha 1 a 3 ajustes realistas.
