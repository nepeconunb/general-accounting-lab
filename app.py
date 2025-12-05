import streamlit as st
import pandas as pd
from datetime import date

# -------------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# -------------------------------------------------------------------
st.set_page_config(
    page_title="General Accounting Lab",
    page_icon="📘",
    layout="wide",
)

# -------------------------------------------------------------------
# INICIALIZAÇÃO DO ESTADO
# -------------------------------------------------------------------
def init_plano_contas():
    """Cria um plano de contas padrão se ainda não existir."""
    dados = [
        # código, nome, grupo, natureza, é caixa?
        ("1.1.1", "Caixa", "Ativo", "Devedora", True),
        ("1.1.2", "Bancos Conta Movimento", "Ativo", "Devedora", True),
        ("1.1.3", "Clientes", "Ativo", "Devedora", False),
        ("1.1.4", "Estoques", "Ativo", "Devedora", False),
        ("1.2.1", "Imobilizado", "Ativo", "Devedora", False),
        ("2.1.1", "Fornecedores", "Passivo", "Credora", False),
        ("2.1.2", "Empréstimos a Pagar", "Passivo", "Credora", False),
        ("2.2.1", "Obrigações Trabalhistas", "Passivo", "Credora", False),
        ("2.2.2", "Obrigações Fiscais", "Passivo", "Credora", False),
        ("2.3.1", "Capital Social", "Patrimônio Líquido", "Credora", False),
        ("2.3.2", "Reservas de Lucros", "Patrimônio Líquido", "Credora", False),
        ("3.1.1", "Receita de Vendas", "Resultado - Receita", "Credora", False),
        ("3.1.2", "Outras Receitas Operacionais", "Resultado - Receita", "Credora", False),
        ("4.1.1", "Custo das Mercadorias Vendidas", "Resultado - Despesa", "Devedora", False),
        ("4.1.2", "Despesas com Pessoal", "Resultado - Despesa", "Devedora", False),
        ("4.1.3", "Despesas Administrativas", "Resultado - Despesa", "Devedora", False),
        ("4.1.4", "Despesas Financeiras", "Resultado - Despesa", "Devedora", False),
    ]
    df = pd.DataFrame(
        dados,
        columns=["codigo", "conta", "grupo", "natureza", "eh_caixa"],
    )
    return df


if "plano_contas" not in st.session_state:
    st.session_state["plano_contas"] = init_plano_contas()

if "lancamentos" not in st.session_state:
    st.session_state["lancamentos"] = pd.DataFrame(
        columns=[
            "data",
            "historico",
            "conta_debito",
            "conta_credito",
            "valor",
        ]
    )

# -------------------------------------------------------------------
# FUNÇÕES DE CÁLCULO
# -------------------------------------------------------------------
def calcula_balancete(plano_contas: pd.DataFrame, lancamentos: pd.DataFrame) -> pd.DataFrame:
    """Retorna balancete de verificação a partir dos lançamentos."""
    bal = plano_contas.copy().reset_index(drop=True)
    bal["debito"] = 0.0
    bal["credito"] = 0.0

    # Soma débitos e créditos por conta
    for _, l in lancamentos.iterrows():
        mask_d = bal["codigo"] == l["conta_debito"]
        mask_c = bal["codigo"] == l["conta_credito"]
        bal.loc[mask_d, "debito"] += l["valor"]
        bal.loc[mask_c, "credito"] += l["valor"]

    # Cálculo dos saldos de acordo com a natureza da conta
    saldos = []
    saldo_dev = []
    saldo_cred = []
    for _, row in bal.iterrows():
        if row["natureza"] == "Devedora":
            s = row["debito"] - row["credito"]
            sd = max(s, 0)
            sc = max(-s, 0)
        else:  # Credora
            s = row["credito"] - row["debito"]
            sc = max(s, 0)
            sd = max(-s, 0)
        saldos.append(s)
        saldo_dev.append(sd)
        saldo_cred.append(sc)

    bal["saldo"] = saldos
    bal["saldo_devedor"] = saldo_dev
    bal["saldo_credor"] = saldo_cred
    return bal


def calcula_dre(balancete: pd.DataFrame) -> pd.DataFrame:
    """Monta DRE simplificada a partir do balancete."""
    receitas = balancete[balancete["grupo"] == "Resultado - Receita"].copy()
    despesas = balancete[balancete["grupo"] == "Resultado - Despesa"].copy()

    receitas["valor"] = receitas["saldo_credor"]
    despesas["valor"] = despesas["saldo_devedor"]

    total_receitas = receitas["valor"].sum()
    total_despesas = despesas["valor"].sum()
    lucro_liquido = total_receitas - total_despesas

    linhas = []
    linhas.append(("Receitas", "", total_receitas))
    linhas.append(("(-) Despesas", "", -total_despesas))
    linhas.append(("= Lucro / Prejuízo do Período", "", lucro_liquido))

    dre = pd.DataFrame(linhas, columns=["descrição", "detalhe", "valor"])
    return dre, lucro_liquido


def calcula_balanco(balancete: pd.DataFrame) -> dict:
    """Retorna dicionário com DataFrames do Balanço Patrimonial."""
    ativo = balancete[balancete["grupo"] == "Ativo"].copy()
    passivo = balancete[balancete["grupo"] == "Passivo"].copy()
    pl = balancete[balancete["grupo"] == "Patrimônio Líquido"].copy()

    # Considera saldos devedores para Ativo e credores para Passivo/PL
    ativo["valor"] = ativo["saldo_devedor"]
    passivo["valor"] = passivo["saldo_credor"]
    pl["valor"] = pl["saldo_credor"]

    return {
        "ativo": ativo[["codigo", "conta", "valor"]],
        "passivo": passivo[["codigo", "conta", "valor"]],
        "pl": pl[["codigo", "conta", "valor"]],
    }


def calcula_fluxo_caixa_direto(
    plano_contas: pd.DataFrame, lancamentos: pd.DataFrame
) -> pd.DataFrame:
    """Fluxo de caixa pelo método direto (simplificado)."""
    if lancamentos.empty:
        return pd.DataFrame(columns=["tipo", "grupo_contraparte", "entrada", "saida"])

    contas_caixa = plano_contas[plano_contas["eh_caixa"]]["codigo"].tolist()
    plano = plano_contas.set_index("codigo")

    linhas = []

    for _, l in lancamentos.iterrows():
        deb = l["conta_debito"]
        cred = l["conta_credito"]
        valor = l["valor"]

        if deb in contas_caixa and cred not in contas_caixa:
            grupo = plano.loc[cred, "grupo"]
            linhas.append(("Entrada de Caixa", grupo, valor, 0.0))
        elif cred in contas_caixa and deb not in contas_caixa:
            grupo = plano.loc[deb, "grupo"]
            linhas.append(("Saída de Caixa", grupo, 0.0, valor))

    if not linhas:
        return pd.DataFrame(columns=["tipo", "grupo_contraparte", "entrada", "saida"])

    df = pd.DataFrame(
        linhas, columns=["tipo", "grupo_contraparte", "entrada", "saida"]
    )
    resumo = (
        df.groupby(["tipo", "grupo_contraparte"], as_index=False)[["entrada", "saida"]]
        .sum()
        .sort_values(["tipo", "grupo_contraparte"])
    )
    return resumo


def calcula_fluxo_caixa_indireto(
    balancete: pd.DataFrame, fluxo_direto: pd.DataFrame, lucro_liquido: float
) -> pd.DataFrame:
    """Fluxo de caixa indireto bem simplificado, apenas para fins didáticos."""
    # Variação de caixa: saldo final de contas de caixa
    caixa = balancete[balancete["eh_caixa"]].copy()
    caixa["valor"] = caixa["saldo"]
    variacao_caixa = caixa["valor"].sum()

    # Caixa líquido de operações via método direto
    if fluxo_direto.empty:
        caixa_oper = 0.0
    else:
        fluxo_direto["saldo"] = fluxo_direto["entrada"] - fluxo_direto["saida"]
        caixa_oper = fluxo_direto["saldo"].sum()

    # Neste modelo simples, supomos que toda variação de caixa é operacional.
    # Ajuste do capital de giro = Caixa Operacional - Lucro Líquido
    ajuste_capital_giro = caixa_oper - lucro_liquido

    linhas = [
        ("Lucro / Prejuízo do Período", lucro_liquido),
        ("(+/-) Ajustes no capital de giro (simplificado)", ajuste_capital_giro),
        ("= Caixa líquido das atividades operacionais", caixa_oper),
        ("Variação de Caixa no Período", variacao_caixa),
    ]
    df = pd.DataFrame(linhas, columns=["descrição", "valor"])
    return df


# -------------------------------------------------------------------
# INTERFACE
# -------------------------------------------------------------------
st.sidebar.title("📘 General Accounting Lab")
menu = st.sidebar.radio(
    "Navegação",
    [
        "Apresentação",
        "Plano de Contas",
        "Lançamentos",
        "Balancete",
        "Balanço Patrimonial",
        "Demonstração do Resultado",
        "Fluxo de Caixa",
    ],
)

plano_contas = st.session_state["plano_contas"]
lancamentos = st.session_state["lancamentos"]

# -------------------------------------------------------------------
# 1. APRESENTAÇÃO
# -------------------------------------------------------------------
if menu == "Apresentação":
    st.title("General Accounting Lab")
    st.markdown(
        """
Bem-vinda(o) ao **General Accounting Lab**!  

Este ambiente foi pensado para uso didático em Contabilidade Geral:

- 👩🏽‍🏫 Registrar lançamentos contábeis (débito × crédito)  
- 📊 Visualizar **Balancete de verificação**  
- 📑 Montar **Balanço Patrimonial** e **Demonstração do Resultado (DRE)**  
- 💰 Gerar um **Fluxo de Caixa** (método direto e versão didática do método indireto)

Use o menu lateral para navegar pelas etapas.  
Você pode editar o plano de contas, registrar lançamentos e observar,
em tempo real, como as demonstrações são afetadas.
        """
    )

# -------------------------------------------------------------------
# 2. PLANO DE CONTAS
# -------------------------------------------------------------------
elif menu == "Plano de Contas":
    st.title("Plano de Contas")

    st.markdown(
        """
Aqui você pode **visualizar e ajustar** o plano de contas usado pelo sistema.

- **Grupo**: Ativo, Passivo, Patrimônio Líquido, Resultado – Receita, Resultado – Despesa  
- **Natureza**: Devedora ou Credora (para cálculo de saldos)  
- **É caixa?**: marque apenas contas de **Caixa e Equivalentes de Caixa**  
        """
    )

    edited = st.data_editor(
        plano_contas,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_plano_contas",
    )

    st.session_state["plano_contas"] = edited
    st.success("Plano de contas atualizado na memória da aplicação.")

# -------------------------------------------------------------------
# 3. LANÇAMENTOS
# -------------------------------------------------------------------
elif menu == "Lançamentos":
    st.title("Lançamentos Contábeis")

    if plano_contas.empty:
        st.warning("O plano de contas está vazio. Preencha-o antes de registrar lançamentos.")
    else:
        with st.form("form_lancamento"):
            col1, col2 = st.columns(2)
            data_lcto = col1.date_input("Data do lançamento", value=date.today())
            historico = col2.text_input("Histórico", "")

            col3, col4 = st.columns(2)
            contas_combo = plano_contas["codigo"] + " - " + plano_contas["conta"]
            conta_debito = col3.selectbox("Conta de Débito", contas_combo)
            conta_credito = col4.selectbox("Conta de Crédito", contas_combo)

            valor = st.number_input(
                "Valor do lançamento",
                min_value=0.01,
                step=0.01,
                format="%.2f",
            )

            submitted = st.form_submit_button("Incluir lançamento")

        if submitted:
            cod_deb = conta_debito.split(" - ")[0]
            cod_cred = conta_credito.split(" - ")[0]
            novo = pd.DataFrame(
                [
                    {
                        "data": data_lcto,
                        "historico": historico,
                        "conta_debito": cod_deb,
                        "conta_credito": cod_cred,
                        "valor": float(valor),
                    }
                ]
            )
            st.session_state["lancamentos"] = pd.concat(
                [st.session_state["lancamentos"], novo],
                ignore_index=True,
            )
            st.success("Lançamento incluído com sucesso!")

        st.subheader("Lançamentos do período")
        if st.session_state["lancamentos"].empty:
            st.info("Ainda não há lançamentos registrados.")
        else:
            st.dataframe(st.session_state["lancamentos"], use_container_width=True)

        if st.button("Limpar todos os lançamentos"):
            st.session_state["lancamentos"] = pd.DataFrame(
                columns=[
                    "data",
                    "historico",
                    "conta_debito",
                    "conta_credito",
                    "valor",
                ]
            )
            st.success("Todos os lançamentos foram apagados.")

# -------------------------------------------------------------------
# 4. BALANCETE
# -------------------------------------------------------------------
elif menu == "Balancete":
    st.title("Balancete de Verificação")

    if lancamentos.empty:
        st.info("Não há lançamentos para gerar o balancete.")
    else:
        balancete = calcula_balancete(plano_contas, lancamentos)
        st.dataframe(balancete[
            [
                "codigo",
                "conta",
                "grupo",
                "debito",
                "credito",
                "saldo_devedor",
                "saldo_credor",
            ]
        ], use_container_width=True)

        total_debitos = balancete["debito"].sum()
        total_creditos = balancete["credito"].sum()
        st.markdown("---")
        col1, col2 = st.columns(2)
        col1.metric("Total de Débitos", f"{total_debitos:,.2f}")
        col2.metric("Total de Créditos", f"{total_creditos:,.2f}")

        if abs(total_debitos - total_creditos) < 0.01:
            st.success("Balancete em equilíbrio (Débitos = Créditos).")
        else:
            st.error("O balancete não está equilibrado. Verifique os lançamentos.")

# -------------------------------------------------------------------
# 5. BALANÇO PATRIMONIAL
# -------------------------------------------------------------------
elif menu == "Balanço Patrimonial":
    st.title("Balanço Patrimonial")

    if lancamentos.empty:
        st.info("Não há lançamentos para montar o Balanço Patrimonial.")
    else:
        balancete = calcula_balancete(plano_contas, lancamentos)
        bp = calcula_balanco(balancete)

        col_esq, col_dir = st.columns(2)

        with col_esq:
            st.subheader("Ativo")
            if bp["ativo"].empty:
                st.write("Sem contas de ativo com saldo.")
            else:
                st.dataframe(bp["ativo"], use_container_width=True)
                st.markdown(
                    f"**Total do Ativo:** {bp['ativo']['valor'].sum():,.2f}"
                )

        with col_dir:
            st.subheader("Passivo")
            if bp["passivo"].empty:
                st.write("Sem contas de passivo com saldo.")
            else:
                st.dataframe(bp["passivo"], use_container_width=True)
                st.markdown(
                    f"**Total do Passivo:** {bp['passivo']['valor'].sum():,.2f}"
                )

            st.subheader("Patrimônio Líquido")
            if bp["pl"].empty:
                st.write("Sem contas de patrimônio líquido com saldo.")
            else:
                st.dataframe(bp["pl"], use_container_width=True)
                st.markdown(
                    f"**Total do Patrimônio Líquido:** {bp['pl']['valor'].sum():,.2f}"
                )

        total_ativo = bp["ativo"]["valor"].sum()
        total_ppl = bp["passivo"]["valor"].sum() + bp["pl"]["valor"].sum()

        st.markdown("---")
        st.metric("Total do Ativo", f"{total_ativo:,.2f}")
        st.metric("Total do Passivo + PL", f"{total_ppl:,.2f}")

# -------------------------------------------------------------------
# 6. DRE
# -------------------------------------------------------------------
elif menu == "Demonstração do Resultado":
    st.title("Demonstração do Resultado do Exercício (DRE)")

    if lancamentos.empty:
        st.info("Não há lançamentos para montar a DRE.")
    else:
        balancete = calcula_balancete(plano_contas, lancamentos)
        dre, lucro = calcula_dre(balancete)

        st.dataframe(dre, use_container_width=True)
        st.markdown("---")
        st.metric("Lucro / Prejuízo do período", f"{lucro:,.2f}")

# -------------------------------------------------------------------
# 7. FLUXO DE CAIXA
# -------------------------------------------------------------------
elif menu == "Fluxo de Caixa":
    st.title("Fluxo de Caixa")

    if lancamentos.empty:
        st.info("Não há lançamentos para gerar o fluxo de caixa.")
    else:
        balancete = calcula_balancete(plano_contas, lancamentos)
        fluxo_direto = calcula_fluxo_caixa_direto(plano_contas, lancamentos)
        dre, lucro = calcula_dre(balancete)
        fluxo_indireto = calcula_fluxo_caixa_indireto(
            balancete, fluxo_direto, lucro
        )

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Método Direto (simplificado)")
            if fluxo_direto.empty:
                st.write("Nenhuma movimentação de contas de caixa foi identificada.")
            else:
                fluxo_direto["saldo"] = fluxo_direto["entrada"] - fluxo_direto["saida"]
                st.dataframe(fluxo_direto, use_container_width=True)
                caixa_oper = fluxo_direto["saldo"].sum()
                st.markdown(
                    f"**Caixa líquido das atividades operacionais (direto):** {caixa_oper:,.2f}"
                )

        with col2:
            st.subheader("Método Indireto (didático)")
            st.dataframe(fluxo_indireto, use_container_width=True)

        st.markdown(
            """
> 🔎 **Observação didática:**  
> O método indireto aqui apresentado é uma versão simplificada,
> apenas para conectar o lucro contábil à variação de caixa observada
> nas contas classificadas como equivalentes de caixa.
            """
        )
