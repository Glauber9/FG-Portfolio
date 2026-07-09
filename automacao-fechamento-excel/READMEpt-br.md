# 💳 Automação de Fechamento de Caixa

Solução automatizada para o processo de fechamento financeiro diário e conciliação de vendas entre duas ou mais máquinas de cartão de diferentes adquirentes, construída inteiramente em **Excel + Power Query**.

> ⚠️ **Nota sobre os dados**: todos os valores de venda, datas e volumes exibidos neste projeto (planilha, prints e vídeos) são **fictícios**, gerados apenas para fins de demonstração. Nenhum dado real de clientes, transações ou faturamento é exposto.


---

## 🎯 O Problema

O fechamento de caixa era um processo **100% manual**: copiar valores de cada máquina de cartão, comparar com o sistema interno, digitar diferenças e montar o relatório do dia. Além do tempo operacional gasto, essa rotina era vulnerável a **erros humanos de digitação e conciliação**, o que gerava ainda mais retrabalho e horas de auditoria quando algo não batia.

## ✅ A Solução

Com a automação via Power Query, o fechamento — que antes levava um tempo considerável todos os dias — agora é concluído em **menos de 1 minuto**. Divergências entre sistema e máquinas, que antes exigiam horas de busca manual, hoje são identificadas e sinalizadas automaticamente no próprio painel.

![Demonstração do Atualizar Tudo](./pic/demo-atualizar.gif)


---

## 🏗️ Arquitetura do Projeto

A parte principal deste projeto não é o visual — é a arquitetura por trás dele:

```
CSV bruto (adquirente)  →  Tabela nativa Excel  →  Power Query (ETL)  →  Dashboard
   (7Pay / Sipag)          (Vendas 7Pay/Sipag)     (limpeza + regras)      (KPIs)
```

1. **Camada de ETL (Power Query)**: em vez de colagem manual, o Power Query se conecta às tabelas de origem e trata os dados extraídos dos sistemas das adquirentes.
2. **Tratamento de Dados**: filtros automáticos removem registros vazios/inúteis, padronizam nomenclatura ("pix" → "Pix", "Debito" → "Débito" etc.) e formatam datas/horas.
3. **Regras de Negócio**: cálculo automático de divergências entre o valor do sistema interno e o valor batido pelas máquinas, com tratamento de erro (`IFERROR`) e arredondamento para eliminar ruído de ponto flutuante do Excel.
4. **Parâmetros dinâmicos**: uma tabela de configuração (`Filtro_Periodo`) define o intervalo de datas do fechamento, usada por todas as consultas — basta alterar duas células para reprocessar tudo.

![Editor Avançado do Power Query](./pic/power-query-editor.png)


---

## 🔄 Como Importar Novos Dados

Um dos pontos centrais da automação é que **atualizar o fechamento não exige nenhuma fórmula manual** — só colar os dados novos e atualizar. O fluxo é:

1. Baixe o relatório do dia exportado pelo painel da adquirente (7Pay ou Sipag), normalmente em `.csv`.
2. Abra o arquivo exportado e copie apenas as **linhas de dados** (sem a linha de cabeçalho).
3. Cole essas linhas logo abaixo da última linha da tabela correspondente — `Tabela_7Pay` na aba *Vendas 7Pay*, ou `Tabela_Sipag` na aba *Vendas Sipag*. Por serem Tabelas nativas do Excel, elas se expandem automaticamente para incluir as novas linhas.
4. Volte para o Dashboard e clique em **Dados → Atualizar Tudo** (ou `Ctrl+Alt+F5`).
5. Todas as consultas (`Filtro_Periodo`, `Tabela_7Pay`, `Tabela_Sipag`, `Dados_do_Grafico`) são reprocessadas automaticamente e o painel é atualizado com os novos números — sem digitar nada manualmente.


---

## 📊 Estrutura da Planilha

| Aba | Função |
|---|---|
| `Dashboard` | Painel visual com KPIs, gráficos e comparação Sistema x Máquinas |
| `Vendas 7Pay` / `Vendas Sipag` | Tabelas nativas onde os dados brutos exportados são carregados |
| `Fechamento 7Pay` / `Fechamento Sipag` | Dados já tratados pelo Power Query, prontos para o Dashboard |
| `Configuração` | Parâmetros do período de análise (`Filtro_Periodo`) e dados auxiliares do gráfico por horário |

![Consultas e Conexões do Power Query](./pic/consultas-conexoes.png)


---

## 🎨 O Dashboard

A aba principal foi desenhada seguindo padrões modernos de UI:

- Fundo limpo e sem linhas de grade, para reduzir a poluição visual e manter o foco nos números.
- Cards isolados para destacar os KPIs mais importantes (faturamento por forma de pagamento, ticket médio, divergências).
- Gráficos interativos (rosca de participação por forma de pagamento + linha de vendas por horário) para leitura rápida do comportamento do dia.

![Dashboard Fechamento](./pic/dashboard.png)

---

## 🛠️ Tecnologias

`Excel` · `Power Query (M)` · `Power Pivot`

---

## 📂 Acesso ao Arquivo

[Clique aqui para baixar a planilha](https://github.com/Glauber9/FG-Portfolio/blob/main/automacao-fechamento-excel/Planilha_de_automacao_de_fechamento.xlsx)

---

## 🚀 Próximos Passos (V2)

Este projeto serve de base para a **Versão 2**, que será desenvolvida e lançada posteriormente, onde toda a lógica hoje implementada em Power Query será migrada para:

- Scripts em **Python** para o ETL
- Banco de dados **PostgreSQL**
- Relatórios dinâmicos em **Power BI**
