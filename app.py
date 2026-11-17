
import streamlit as st
import pandas as pd
import sqlite3
import re
import json
from openai import OpenAI
import os

chave_api = os.environ.get("OPENAI_API_KEY")

cliente_ia = OpenAI(api_key=chave_api)

# PROTEÇÃO DE DADOS — MÁSCARA DE INFORMAÇÕES

def mascarar_dados(texto):

    texto = re.sub(
        r'\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b',
        '[EMAIL PROTEGIDO]',
        texto
    )

    texto = re.sub(
        r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b',
        '[CPF PROTEGIDO]',
        texto
    )

    texto = re.sub(
        r'\b\d{5}-?\d{3}\b',
        '[CEP PROTEGIDO]',
        texto
    )

    texto = re.sub(
        r'(?<!\d)(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[-.\s]?\d{4}(?!\d)',
        '[TELEFONE PROTEGIDO]',
        texto
    )

    return texto


# CATEGORIAS DE TRIAGEM

CATEGORIAS_OCORRENCIA = [
    "Atraso na entrega",
    "Erro no pedido",
    "Problema de endereço",
    "Problema com medicamento",
    "Problema de temperatura",
    "Suspeita de incidente com dados",
    "Outros"
]


# ESTRUTURA DA RESPOSTA

ESTRUTURA_TRIAGEM = {
    "categoria": "",
    "prioridade": "",
    "risco": "",
    "escalonamento_humano": False,
    "justificativa": "",
    "acao_recomendada": ""
}
PROMPT_TRIAGEM = """
Você é um assistente de triagem operacional
de um hub de entregas para farmácias de manipulação.

Analise a ocorrência recebida e classifique:

1. Categoria:
Escolha OBRIGATORIAMENTE uma destas opções, copiando o texto exatamente:

- Atraso na entrega
- Erro no pedido
- Problema de endereço
- Problema com medicamento
- Problema de temperatura
- Suspeita de incidente com dados
- Outros

Não crie categorias novas. Não abrevie nem altere os nomes.

2. Prioridade:
Baixa, Média, Alta ou Crítica.

3. Risco:
Baixo, Moderado, Alto ou Crítico.

4. Escalonamento humano:
Use true quando houver necessidade de avaliação humana.

REGRAS OBRIGATÓRIAS:

- Problemas com medicamentos exigem avaliação humana.
- Problemas de temperatura exigem avaliação humana.
- Suspeitas de incidentes com dados exigem avaliação humana.
- Situações envolvendo medicamentos controlados exigem avaliação humana.
- Nunca recomende ignorar incidentes ou riscos.
- Não invente informações ausentes.
- Seja objetivo na justificativa e na ação recomendada.

Retorne exclusivamente um JSON válido com os campos:

categoria
prioridade
risco
escalonamento_humano
justificativa
acao_recomendada
"""

PRIORIDADES_TRIAGEM = [
    "Baixa",
    "Média",
    "Alta",
    "Crítica"
]


NIVEIS_RISCO = [
    "Baixo",
    "Moderado",
    "Alto",
    "Crítico"
]


# VALIDAR RESULTADO DA TRIAGEM


def validar_triagem(resultado):
        if not isinstance(resultado, dict):
            return False

        campos_obrigatorios = [
            "categoria",
            "prioridade",
            "risco",
            "escalonamento_humano",
            "justificativa",
            "acao_recomendada"
        ]

        if not all(campo in resultado for campo in campos_obrigatorios):
            return False

        if resultado["categoria"] not in CATEGORIAS_OCORRENCIA:
            return False

        if resultado["prioridade"] not in PRIORIDADES_TRIAGEM:
            return False

        if resultado["risco"] not in NIVEIS_RISCO:
            return False

        if not isinstance(resultado["escalonamento_humano"], bool):
            return False

        categorias_que_exigem_humano = [
            "Problema com medicamento",
            "Problema de temperatura",
            "Suspeita de incidente com dados"
        ]

        if (
            resultado["categoria"] in categorias_que_exigem_humano
            and resultado["escalonamento_humano"] is not True
        ):
            return False

        return True

    
    # FUNÇÃO PRINCIPAL DE TRIAGEM


def triar_ocorrencia(texto):
    conexao = sqlite3.connect("urban_density.db")

    try:
        texto_protegido = mascarar_dados(texto)

        resposta = cliente_ia.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": PROMPT_TRIAGEM
                },
                {
                    "role": "user",
                    "content": texto_protegido
                }
            ],
            response_format={"type": "json_object"}
        )

        resultado = json.loads(
            resposta.choices[0].message.content
        )

        if not validar_triagem(resultado):
            raise ValueError("Resposta da IA fora do formato esperado.")

        conexao.execute("""
            INSERT INTO triagens (
                texto_protegido,
                categoria,
                prioridade,
                risco,
                escalonamento_humano,
                justificativa,
                acao_recomendada,
                data_hora
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            texto_protegido,
            resultado["categoria"],
            resultado["prioridade"],
            resultado["risco"],
            resultado["escalonamento_humano"],
            resultado["justificativa"],
            resultado["acao_recomendada"],
            pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conexao.commit()

        return {
            "texto_protegido": texto_protegido,
            "triagem": resultado
        }

    finally:
        conexao.close()


# TESTES AUTOMATIZADOS
st.subheader("Testes de segurança do agente")
casos_teste = [
    {
        "categoria": "Problema com medicamento",
        "escalonamento_humano": False,
        "esperado": False
    },
    {
        "categoria": "Problema de temperatura",
        "escalonamento_humano": False,
        "esperado": False
    },
    {
        "categoria": "Suspeita de incidente com dados",
        "escalonamento_humano": False,
        "esperado": False
    },
    {
        "categoria": "Atraso na entrega",
        "escalonamento_humano": False,
        "esperado": True
    }
]

    # TESTE DA FUNÇÃO PRINCIPAL

ocorrencia_teste = """
Cliente: João
CPF: 123.456.789-00
Telefone: (22) 99999-8888
Problema: pedido atrasado.
"""

# resultado_ocorrencia = triar_ocorrencia(ocorrencia_teste)

st.subheader("Triagem inteligente de ocorrências")

texto_ocorrencia = st.text_area(
    "Descreva a ocorrência:",
    placeholder="Ex.: Pedido atrasado na entrega..."
)
st.subheader("Teste do agente de triagem")

if st.button("Executar triagem com IA"):
    if texto_ocorrencia.strip():
        try:
            resultado_ocorrencia = triar_ocorrencia(texto_ocorrencia)

            st.success("Triagem concluída!")

            st.subheader("Resultado da análise")
            st.json(resultado_ocorrencia["triagem"])

        except Exception as erro:
            st.error(f"Erro na triagem: {erro}")

    else:
        st.warning("Digite uma ocorrência antes de executar.")
        
# st.write(resultado_ocorrencia)

# TESTE DE VALIDAÇÃO

resultado_teste = {
    "categoria": "Atraso na entrega",
    "prioridade": "Alta",
    "risco": "Moderado",
    "escalonamento_humano": True,
    "justificativa": "A entrega está atrasada.",
    "acao_recomendada": "Verificar com o entregador."
}

st.write("Teste de validação:", validar_triagem(resultado_teste))
resultado_invalido = {
    "categoria": "Categoria inexistente",
    "prioridade": "Alta",
    "risco": "Moderado",
    "escalonamento_humano": True,
    "justificativa": "Teste de erro.",
    "acao_recomendada": "Revisar."
}
resultado_prioridade_invalida = {
    "categoria": "Atraso na entrega",
    "prioridade": "Urgente",
    "risco": "Moderado",
    "escalonamento_humano": True,
    "justificativa": "Teste de prioridade.",
    "acao_recomendada": "Revisar."
}
resultado_escalonamento_invalido = {
    "categoria": "Atraso na entrega",
    "prioridade": "Alta",
    "risco": "Moderado",
    "escalonamento_humano": "Sim",
    "justificativa": "Teste de escalonamento.",
    "acao_recomendada": "Revisar."
}

st.write(
    "Teste de escalonamento inválido:",
    validar_triagem(resultado_escalonamento_invalido)
)

resultado_incompleto = {
    "categoria": "Atraso na entrega",
    "prioridade": "Alta"
}

st.write(
    "Teste de resposta incompleta:",
    validar_triagem(resultado_incompleto)
)

st.write(
    "Teste de prioridade inválida:",
    validar_triagem(resultado_prioridade_invalida)
)

st.write("Teste de categoria inválida:", validar_triagem(resultado_invalido))

# CONFIGURAÇÃO
st.set_page_config(
    page_title="Urban Density Hub",
    page_icon="📦",
    layout="wide"
)


# BANCO DE DADOS
conexao = sqlite3.connect(
    "urban_density.db",
    check_same_thread=False
)

conexao.execute("""
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE,
        status TEXT,
        entregador TEXT,
        valor REAL
    )
""")

conexao.commit()

# ADICIONAR REGIÃO À TABELA DE PEDIDOS
colunas_pedidos = [
    coluna[1]
    for coluna in conexao.execute(
        "PRAGMA table_info(pedidos)"
    ).fetchall()
]

if "regiao" not in colunas_pedidos:
    conexao.execute(
        "ALTER TABLE pedidos ADD COLUMN regiao TEXT"
    )
    conexao.commit()

# TABELA DE HISTÓRICO

conexao.execute("""
    CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido TEXT,
        acao TEXT,
        detalhe TEXT,
        data_hora TEXT
    )
""")
conexao.execute("""
    CREATE TABLE IF NOT EXISTS ocorrencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido TEXT,
        categoria TEXT,
        descricao TEXT,
        data_hora TEXT,
        responsavel TEXT
    )
""")
conexao.commit()
conexao.execute("""
    CREATE TABLE IF NOT EXISTS triagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        texto_protegido TEXT,
        categoria TEXT,
        prioridade TEXT,
        risco TEXT,
        escalonamento_humano BOOLEAN,
        justificativa TEXT,
        acao_recomendada TEXT,
        data_hora TEXT
    )
""")
conexao.commit()

colunas = [
    coluna[1]
    for coluna in conexao.execute(
        "PRAGMA table_info(ocorrencias)"
    ).fetchall()
]
if "responsavel" not in colunas:
    conexao.execute(
        "ALTER TABLE ocorrencias ADD COLUMN responsavel TEXT"
    )
    conexao.commit()

# FUNÇÃO PARA CARREGAR OS PEDIDOS
def carregar_pedidos():
    dados = conexao.execute("""
        SELECT numero, status, entregador, valor, regiao
        FROM pedidos
        ORDER BY id
    """).fetchall()

    return [
        {
            "Pedido": linha[0],
            "Status": linha[1],
            "Entregador": linha[2],
            "Valor (R$)": linha[3],
            "Região": linha[4]
        }
        for linha in dados
    ]


# CABEÇALHO
st.title("Urban Density Hub")
st.caption("Gestão operacional e inteligência de entregas")

entregadores = [
    "Motoboy 1",
    "Motoboy 2",
    "Motoboy 3"
]

pedidos = carregar_pedidos()

# INDICADORES
pendentes = sum(
    1 for p in pedidos if p["Status"] == "Pendente"
)

em_rota = sum(
    1 for p in pedidos if p["Status"] == "Em rota"
)

concluidos = sum(
    1 for p in pedidos if p["Status"] == "Concluído"
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Pedidos pendentes", pendentes)
col2.metric("Entregas em rota", em_rota)
col3.metric("Entregas concluídas", concluidos)
col4.metric(
    "Valor dos pedidos",
    f"R$ {sum(p['Valor (R$)'] for p in pedidos):.2f}"
)


# INTELIGÊNCIA ECONÔMICA

# Parâmetro demonstrativo: custo estimado por entrega
CUSTO_POR_ENTREGA = 8.00

# Considera somente pedidos concluídos
pedidos_concluidos = [
    p for p in pedidos
    if p["Status"] == "Concluído"
]

# Receita efetivamente concluída
receita_concluida = sum(
    p["Valor (R$)"] for p in pedidos_concluidos
)

# Custo operacional estimado
custo_operacional = (
    len(pedidos_concluidos) * CUSTO_POR_ENTREGA
)

# Margem operacional estimada
margem_estimada = (
    receita_concluida - custo_operacional
)

st.subheader("Inteligência Econômica")

col5, col6, col7 = st.columns(3)

col5.metric(
    "Receita concluída",
    f"R$ {receita_concluida:.2f}"
)

col6.metric(
    "Custo operacional estimado",
    f"R$ {custo_operacional:.2f}"
)

col7.metric(
    "Margem estimada",
    f"R$ {margem_estimada:.2f}",
    delta=f"{margem_estimada / receita_concluida * 100:.1f}% de margem"
    if receita_concluida > 0 else None
)

st.caption(
    "Custos calculados com parâmetro demonstrativo de "
    f"R$ {CUSTO_POR_ENTREGA:.2f} por entrega concluída. "
    "Não representam lucro contábil."
)

# PRODUTIVIDADE POR ENTREGADOR

st.subheader("Produtividade por entregador")

produtividade = {}

for pedido in pedidos_concluidos:
    entregador = pedido["Entregador"]

    if entregador:
        produtividade[entregador] = (
            produtividade.get(entregador, 0) + 1
        )

if produtividade:
    dados_produtividade = pd.DataFrame(
        list(produtividade.items()),
        columns=["Entregador", "Entregas concluídas"]
    )

    dados_produtividade = dados_produtividade.sort_values(
        by="Entregas concluídas",
        ascending=False
    )

    st.bar_chart(
        dados_produtividade.set_index("Entregador")
    )

    st.dataframe(
        dados_produtividade,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info(
        "Ainda não existem entregas concluídas atribuídas a entregadores."
    )

# DENSIDADE OPERACIONAL POR REGIÃO

st.subheader("Densidade operacional por região")

pedidos_com_regiao = [
    p for p in pedidos
    if p["Região"] and p["Região"].strip()
]

if pedidos_com_regiao:
    densidade = {}

    for pedido in pedidos_com_regiao:
        regiao = pedido["Região"].strip().title()

        densidade[regiao] = (
            densidade.get(regiao, 0) + 1
        )

    dados_densidade = pd.DataFrame(
        list(densidade.items()),
        columns=["Região", "Quantidade de pedidos"]
    )

    dados_densidade = dados_densidade.sort_values(
        by="Quantidade de pedidos",
        ascending=False
    )

    st.bar_chart(
        dados_densidade.set_index("Região")
    )

    st.dataframe(
        dados_densidade,
        use_container_width=True,
        hide_index=True
    )

else:
    st.info(
        "Cadastre pedidos com regiões para visualizar a densidade operacional."
    )

st.divider()

# ANÁLISE ECONÔMICA POR REGIÃO

st.subheader("Resultado econômico por região")

resultado_regional = {}

for pedido in pedidos_com_regiao:
    regiao = pedido["Região"].strip().title()

    if regiao not in resultado_regional:
        resultado_regional[regiao] = {
            "Pedidos": 0,
            "Receita concluída": 0.0,
            "Custo estimado": 0.0
        }

    resultado_regional[regiao]["Pedidos"] += 1

    if pedido["Status"] == "Concluído":
        resultado_regional[regiao]["Receita concluída"] += pedido["Valor (R$)"]
        resultado_regional[regiao]["Custo estimado"] += CUSTO_POR_ENTREGA

if resultado_regional:
    dados_regionais = pd.DataFrame.from_dict(
        resultado_regional,
        orient="index"
    )

    dados_regionais["Margem estimada"] = (
        dados_regionais["Receita concluída"]
        - dados_regionais["Custo estimado"]
    )

    st.dataframe(
        dados_regionais.reset_index(names="Região"),
        use_container_width=True,
        hide_index=True
    )
# CADASTRO DE PEDIDOS
st.subheader("Cadastrar novo pedido")

with st.form("form_pedido"):
    numero = st.text_input("Número do pedido")

    valor = st.number_input(
        "Valor do pedido (R$)",
        min_value=0.01,
        value=25.00,
        step=1.00
    )

    status = st.selectbox(
        "Status",
        ["Pendente", "Em rota", "Concluído"]
    )

    entregador = st.selectbox(
        "Entregador",
        ["Não atribuído"] + entregadores
    )
    regiao = st.text_input(
        "Região de entrega",
        placeholder="Ex.: Centro, Cavaleiros, Imbetiba"
    )
    cadastrar = st.form_submit_button("Cadastrar pedido")

    if cadastrar:
        numero = numero.strip()

        if not numero:
            st.error("Informe o número do pedido.")

        else:
            try:
                conexao.execute("""
                    INSERT INTO pedidos
                    (numero, status, entregador, valor, regiao)
                    VALUES (?, ?, ?, ?, ?)
                """, (numero, status, entregador, valor, regiao.strip()))

                conexao.commit()
                conexao.execute("""
                    INSERT INTO historico
                    (pedido, acao, detalhe, data_hora)
                    VALUES (?, ?, ?, ?)
                """, (
                    numero,
                    "Cadastro",
                    "Pedido cadastrado no sistema",
                    pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
                ))

                conexao.commit()
                st.success("Pedido salvo no banco de dados!")
                st.rerun()

            except sqlite3.IntegrityError:
                st.error("Esse número de pedido já existe.")


st.divider()

# ATUALIZAÇÃO DE PEDIDOS
st.subheader("Atualizar pedido")

pedidos = carregar_pedidos()

if pedidos:
    numeros = [p["Pedido"] for p in pedidos]

    selecionado = st.selectbox(
        "Selecione o pedido",
        numeros
    )

    pedido_atual = next(
        p for p in pedidos
        if p["Pedido"] == selecionado
    )

    with st.form("form_atualizar"):
        novo_status = st.selectbox(
            "Novo status",
            ["Pendente", "Em rota", "Concluído"],
            index=["Pendente", "Em rota", "Concluído"].index(
                pedido_atual["Status"]
            )
        )

        opcoes_entregadores = ["Não atribuído"] + entregadores

        novo_entregador = st.selectbox(
            "Novo entregador",
            opcoes_entregadores,
            index=opcoes_entregadores.index(
                pedido_atual["Entregador"]
            )
        )

        atualizar = st.form_submit_button("Salvar alterações")

        if atualizar:
            conexao.execute("""
                UPDATE pedidos
                SET status = ?, entregador = ?
                WHERE numero = ?
            """, (novo_status, novo_entregador, selecionado))

            conexao.commit()

            conexao.execute("""
                INSERT INTO historico
                (pedido, acao, detalhe, data_hora)
                VALUES (?, ?, ?, ?)
            """, (
                selecionado,
                "Atualização",
                f"Status: {pedido_atual['Status']} → {novo_status} | "
                f"Entregador: {pedido_atual['Entregador']} → {novo_entregador}",
                pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
            ))

            conexao.commit()

            st.success("Pedido atualizado e alteração registrada!")
            st.rerun()

else:
    st.info("Ainda não existem pedidos cadastrados.")


st.divider()

# TABELA DE PEDIDOS
st.subheader("Gestão de pedidos")
pedidos = carregar_pedidos()

if pedidos:
    df = pd.DataFrame(pedidos)
    st.dataframe(df, use_container_width=True)
else:
    st.info("Cadastre seu primeiro pedido para visualizar a tabela.")
# REGISTRO DE OCORRÊNCIAS
st.divider()
st.subheader("Registrar ocorrência")

if pedidos:
    with st.form("form_ocorrencia"):
        pedido_ocorrencia = st.selectbox(
            "Pedido relacionado",
            [p["Pedido"] for p in pedidos]
        )

        categoria = st.selectbox(
            "Categoria",
            [
                "Atraso na entrega",
                "Cliente não localizado",
                "Produto danificado",
                "Contestação do cliente",
                "Outro"
            ]
        )

        descricao = st.text_area("Descrição da ocorrência")
        responsavel = st.text_input(
            "Responsável pelo registro",
            placeholder="Ex.: Gerente operacional"
        )
        registrar = st.form_submit_button("Registrar ocorrência")

        if registrar:
            if not descricao.strip():
                st.error("Descreva a ocorrência.")
            else:
                conexao.execute("""
                    INSERT INTO ocorrencias
                    (pedido, categoria, descricao, data_hora, responsavel)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    pedido_ocorrencia,
                    categoria,
                    descricao.strip(),
                    pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S"),
                    responsavel.strip()
                ))
                conexao.commit()
                st.success("Ocorrência registrada!")
                st.rerun()
else:
    st.info("Cadastre um pedido antes de registrar uma ocorrência.")
# HISTÓRICO DE OPERAÇÕES
st.divider()
# CONSULTA DE OCORRÊNCIAS
st.divider()
st.subheader("Ocorrências registradas")

dados_ocorrencias = conexao.execute("""
    SELECT
        pedido AS "Pedido",
        responsavel AS "Responsável",
        categoria AS "Categoria",
        descricao AS "Descrição",
        data_hora AS "Data e horário"
    FROM ocorrencias
    ORDER BY id DESC
""").fetchall()

if dados_ocorrencias:
    df_ocorrencias = pd.DataFrame(
        dados_ocorrencias,
        columns=[
            "Pedido",
            "Responsável",
            "Categoria",
            "Descrição",
            "Data e horário"
        ]
    )

    st.dataframe(
        df_ocorrencias,
        use_container_width=True
    )
else:
    st.info("Ainda não existem ocorrências registradas.")
st.subheader("Histórico de operações")

historico = conexao.execute("""
    SELECT
        pedido AS "Pedido",
        acao AS "Ação",
        detalhe AS "Detalhes",
        data_hora AS "Data e horário"
    FROM historico
    ORDER BY id DESC
""").fetchall()

if historico:
    df_historico = pd.DataFrame(
        historico,
        columns=[
            "Pedido",
            "Ação",
            "Detalhes",
            "Data e horário"
        ]
    )

    st.dataframe(
        df_historico,
        use_container_width=True
    )
else:
    st.info("Ainda não existem operações registradas.")
st.caption("Protótipo em desenvolvimento — dados fictícios.")

st.subheader("Histórico de triagens")

conexao_consulta = sqlite3.connect("urban_density.db")

historico_triagens = pd.read_sql_query(
    "SELECT * FROM triagens ORDER BY id DESC",
    conexao_consulta
)

st.dataframe(historico_triagens, use_container_width=True)

conexao_consulta.close()
