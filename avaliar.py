
import pandas as pd
from triagem import (
    executar_triagem_v2,
    aplicar_escalonamento_deterministico
)

# CARREGAR CASOS
casos = pd.read_csv("casos_teste.csv", sep=";")

# MAPEAR TIPOS DO GABARITO PARA CATEGORIAS DA V1
MAPA_CATEGORIAS = {
    "atraso": "Atraso na entrega",
    "endereco_errado": "Problema de endereço",
    "destinatario_ausente": "Outros",
    "produto_danificado": "Problema com medicamento",
    "conservacao_temperatura": "Problema de temperatura",
    "pedido_fora_de_rota": "Outros",
    "outro": "Outros",
    "alteracao_de_janela": "Outros",
    "medicamento_controlado": "Problema com medicamento",
    "solicitacao_dados_pessoais": "Suspeita de incidente com dados",
    "incidente_de_dados": "Suspeita de incidente com dados"
}

# GABARITO REVISADO — ALTERAÇÕES POR ID
# O gabarito original permanece preservado.

CATEGORIAS_REVISADAS_POR_ID = {
    6: "Outros",
    9: "Outros",
    10: "Erro no pedido",
    13: "Outros",
    15: "Erro no pedido",
    16: "Outros",
    17: "Problema de temperatura",
    21: "Outros",
    26: "Suspeita de incidente com dados",
    28: "Atraso na entrega",
    29: "Suspeita de incidente com dados"
}


def avaliar_casos():
    resultados = []

    for _, caso in casos.iterrows():
        print(f"Avaliando caso {caso['id']}/30...")

        retorno = None
        
        try:
            retorno = executar_triagem_v2(caso["texto"])
            
            if retorno.get("erro_formato"):
                raise ValueError("JSON inválido: " + retorno["erro_formato"])
                
            triagem_modelo = retorno["triagem_modelo"]
            triagem_sistema = retorno["triagem"]
            triagem = triagem_sistema

            categoria_original = MAPA_CATEGORIAS[caso["tipo_esperado"]]
            categoria_esperada = CATEGORIAS_REVISADAS_POR_ID.get(
                int(caso["id"]), categoria_original
            )

            acerto_categoria = (
                triagem["categoria"] == categoria_esperada
            )

            acerto_escalonamento_modelo = (
                triagem_modelo["escalonamento_humano"]
                == (caso["escala_esperada"] == "sim")
            )

            acerto_escalonamento_sistema = (
                triagem_sistema["escalonamento_humano"]
                == (caso["escala_esperada"] == "sim")
            )

            acao_obtida = triagem["acao_recomendada"]
            acao_esperada = caso["acao_esperada"]

            acerto_acao = (
                acao_obtida == acao_esperada
            )

            resultados.append({
                "id": caso["id"],
                "texto_protegido": retorno["texto_protegido"],
                "resposta_bruta": retorno["resposta_bruta"],
                "categoria_obtida": triagem["categoria"],
                "categoria_esperada": categoria_esperada,
                "categoria_original": categoria_original,
                "acerto_categoria": acerto_categoria,
                "acao_obtida": triagem["acao_recomendada"],
                "acao_esperada": acao_esperada,
                "acerto_acao": acerto_acao,
                "escalonamento_modelo": triagem_modelo["escalonamento_humano"],
                "escalonamento_sistema": triagem_sistema["escalonamento_humano"],
                "escalonamento_esperado": caso["escala_esperada"],
                "acerto_escalonamento_modelo": acerto_escalonamento_modelo,
                "acerto_escalonamento_sistema": acerto_escalonamento_sistema,
                "erro": ""
            })

        except Exception as erro:
            resultados.append({
                "id": caso["id"],
                "texto_protegido": (
                    retorno.get("texto_protegido", "") if retorno else ""
                ),
                "resposta_bruta": (
                    retorno.get("resposta_bruta", "") if retorno else ""
                ),
                "categoria_obtida": "ERRO",
                "categoria_esperada": CATEGORIAS_REVISADAS_POR_ID.get(
                    int(caso["id"]),
                    MAPA_CATEGORIAS.get(caso["tipo_esperado"], "DESCONHECIDA")
                ),
                "categoria_original": MAPA_CATEGORIAS.get(
                    caso["tipo_esperado"], "DESCONHECIDA"
                ),
                "acerto_categoria": False,
                "acao_obtida": "ERRO",
                "acao_esperada": caso["acao_esperada"],
                "acerto_acao": False,
                "escalonamento_modelo": "ERRO",
                "escalonamento_sistema": "ERRO",
                "escalonamento_esperado": caso["escala_esperada"],
                "acerto_escalonamento_modelo": False,
                "acerto_escalonamento_sistema": False,
                "erro": str(erro)
            })

    df = pd.DataFrame(resultados)

    df.to_csv(
        "resultados_v2.csv",
        sep=";",
        index=False,
        encoding="utf-8-sig"
    )

    total = len(df)

    print("\n===== RESULTADO DA AVALIAÇÃO V2 =====")
    print(f"Casos avaliados: {total}")
    print(
        f"Acerto de categoria: "
        f"{df['acerto_categoria'].sum()}/{total} "
        f"({df['acerto_categoria'].mean() * 100:.1f}%)"
    )
    print(
        f"Acerto de ação: "
        f"{df['acerto_acao'].sum()}/{total} "
        f"({df['acerto_acao'].mean() * 100:.1f}%)"
    )
    print(
        f"Acerto de escalonamento — MODELO: "
        f"{df['acerto_escalonamento_modelo'].sum()}/{total} "
        f"({df['acerto_escalonamento_modelo'].mean() * 100:.1f}%)"
    )

    print(
        f"Acerto de escalonamento — SISTEMA: "
        f"{df['acerto_escalonamento_sistema'].sum()}/{total} "
        f"({df['acerto_escalonamento_sistema'].mean() * 100:.1f}%)"
    )

    casos_criticos = df[df["id"].between(24, 30)]

    falhas_criticas_modelo = casos_criticos[
        casos_criticos["escalonamento_modelo"] != True
    ]

    falhas_criticas_sistema = casos_criticos[
        casos_criticos["escalonamento_sistema"] != True
    ]

    print(
        f"Falhas críticas — MODELO: "
        f"{len(falhas_criticas_modelo)}/7"
    )

    print(
        f"Falhas críticas — SISTEMA: "
        f"{len(falhas_criticas_sistema)}/7"
    )

    return df


if __name__ == "__main__":
    avaliar_casos()
