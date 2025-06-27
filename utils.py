CORES_EQUIPES = {
    "Visão Geral": "#31333F", "Operação - Salvador": "#0072B2",
    "Operação - Litoral Norte": "#009E73", "Administrativo / Financeiro": "#D55E00",
    "Técnico": "#CC79A7", "Comercial": "#E69F00", "Operação - Industrial": "#56B4E9"
}

MESES_EM_PORTUGUES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

def get_cor_desempenho(taxa):
    return "#00CC96" if taxa >= 90 else "#FFD700" if taxa >= 70 else "#EF553B"
