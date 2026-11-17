# Hub de Última Milha para Farmácias de Manipulação

Protótipo de uma solução logística para agrupar pedidos de diferentes farmácias de manipulação por região, organizar rotas de entrega D+1 e melhorar a eficiência operacional.

## Objetivo

Explorar como tecnologia, dados e inteligência artificial podem ajudar a resolver desafios da logística de última milha em um segmento que exige atenção especial ao tratamento de ocorrências e à segurança das informações.

## Funcionalidades

- Dashboard operacional para acompanhamento de pedidos e ocorrências.
- Gestão de pedidos e seus respectivos status.
- Indicadores de densidade regional e desempenho operacional.
- Agente de IA para triagem de ocorrências.
- Mascaramento de CPF, telefone, e-mail e CEP antes do processamento pela IA.
- Saída estruturada em JSON, com validação de formato e ações permitidas.
- Camada de regras determinísticas para identificação de situações que exigem escalonamento humano.

## Tecnologias utilizadas

- Python
- Streamlit
- SQLite
- API OpenAI (GPT-4o-mini)
- Engenharia de prompts
- Processamento de JSON
- Regras determinísticas de validação e escalonamento

## Avaliação do agente

O agente foi avaliado em um conjunto de 30 casos de teste sintéticos, incluindo situações operacionais e tentativas de prompt injection.

Resultados da segunda versão:

| Métrica | Resultado |
|---|---:|
| Acerto de categoria | 66,7% |
| Acerto de ação | 63,3% |
| Escalonamento do modelo isolado | 80% |
| Escalonamento do sistema combinado | 90% |
| Casos críticos escalonados pelo sistema combinado | 7/7 |

O resultado de 90% considera o modelo combinado com regras determinísticas, e não o modelo isoladamente. Os resultados representam um benchmark sintético inicial, com espaço para melhorias.

## Estrutura do projeto

- `app.py`: aplicação e dashboard Streamlit.
- `triagem.py`: lógica de triagem e integração com a API OpenAI.
- `avaliar.py`: execução da avaliação do agente.
- `casos_teste.csv`: conjunto de casos sintéticos utilizados nos testes.

## Segurança e limitações

- Os dados utilizados no protótipo são sintéticos.
- A chave da API é carregada por variável de ambiente.
- O projeto não está em produção.
- Os resultados não representam economia ou desempenho operacional comprovado em ambiente real.
- A avaliação ainda precisa ser ampliada e validada com revisão humana.

## Motivação

Este projeto foi desenvolvido para explorar a aplicação prática de IA generativa em problemas operacionais reais, combinando engenharia de prompts, integração de APIs, validação estruturada e regras de negócio.

**Status:** Protótipo funcional em desenvolvimento.
