---
name: sac-relatorio-auditoria
description: Use quando o estudante pedir relatório, análise de desempenho, evolução, ou auditoria/verificação da consistência das memórias, ou quando uma validação apontar erros ou avisos.
---

# Relatórios e auditoria

## Relatório
`python3 scripts/sac.py relatorio` gera `08_RELATORIOS/relatorio_semanal.md` (7 dias) e `relatorio_de_desempenho.md` (tudo). Leia o resultado e traduza para o estudante: o que foi estudado, tópicos dominados e em consolidação, evolução, desempenho por tipo de tentativa, erros recorrentes, revisões vencidas, tempo (com os três rótulos), progresso por indicador, risco e próximas prioridades.

Regras: use métricas consistentes ao longo do tempo; mostre **tendências e limitações**, não causas ("melhorou" ≠ "o método funcionou"); nunca produza notas, gráficos ou indicadores sem dados; se faltar dado (tempo efetivo, datas), diga "desconhecido". Se desenhar gráficos, use só os números do relatório.

## Validação (rotina)
`python3 scripts/sac.py validar [--registrar]` verifica: ids e ordem do log, referências (tópicos, questões), campos obrigatórios das questões, origem das datas, sessão obsoleta, visões ausentes/desatualizadas/editadas à mão, fontes novas/alteradas/ausentes e pendências abertas. `--registrar` anexa o resultado a `09_VALIDACAO/log_de_validacao.md`. Exit 1 = há ERRO: corrija (normalmente `render`) ou reporte. Nunca esconda um aviso relevante.

## Auditoria (quando pedida)
Além do `validar`, confira por amostragem, e diga o que de fato conferiu:
1. **Acadêmica:** afirmações dos arquivos de conhecimento batem com a fonte citada? as páginas existem? fórmulas e contas conferem? há divergência entre fontes?
2. **Pedagógica:** a questão mede o objetivo? gabarito coerente com enunciado? critérios explícitos? o domínio atribuído tem evidência (veja a coluna de motivos em `dominio_por_topico.md`)?
3. **Operacional:** sessões registradas? revisões coerentes com a escada? datas com origem? tempo verificável (rótulos corretos)? arquivos manuais em sincronia com o CLI (por exemplo `pre_requisitos.md` × `--prereq`)?

Falhas e correções: `pendencia add --categoria operacional|conflito|fonte --texto "..."` e `pendencia resolver <ID> --nota "..."`. Se algo não puder ser validado, **sinalize a incerteza**.
