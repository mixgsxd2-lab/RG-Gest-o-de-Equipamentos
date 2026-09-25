"""Domínios (listas de valores) usados em todo o sistema."""

ROLES = {
    "admin": "Administrador",
    "gestor": "Gestor de Manutenção",
    "operador": "Operador/Técnico",
    "solicitante": "Solicitante",
    "estoque": "Estoque",
    "diretoria": "Diretoria",
}

MAINTENANCE_TYPES = [
    "Corretiva",
    "Preventiva",
    "Preditiva",
    "Emergencial",
    "Inspeção",
    "Calibração",
    "Instalação",
]

PRIORITIES = ["Baixa", "Média", "Alta", "Urgente"]
CRITICALITIES = ["Baixa", "Média", "Alta", "Crítica"]

# Prazo de solução (SLA) em horas por prioridade
SLA_HOURS = {"Baixa": 72, "Média": 24, "Alta": 8, "Urgente": 4}
SLA_EMERGENCY_HOURS = 2

# Fluxo do chamado: Aberto → Recebido → Aceito → Em execução →
# Aguardando material/terceiro → Finalizado → Encerrado
TICKET_STATUSES = {
    "aberto": "Aberto",
    "recebido": "Recebido",
    "aceito": "Aceito",
    "em_execucao": "Em execução",
    "aguardando": "Aguardando material/terceiro",
    "finalizado": "Finalizado",
    "encerrado": "Encerrado",
    "cancelado": "Cancelado",
}
OPEN_STATUSES = ["aberto", "recebido"]
IN_PROGRESS_STATUSES = ["aceito", "em_execucao", "aguardando"]
DONE_STATUSES = ["finalizado", "encerrado"]

ASSET_STATUSES = ["Operacional", "Em manutenção", "Inoperante", "Reserva", "Desativado"]
ASSET_KINDS = ["Equipamento", "Estrutura/Instalação"]

COST_CATEGORIES = ["Material", "Mão de obra", "Terceiros", "Contrato", "Investimento"]

SENSOR_KINDS = {
    "energia": "Energia elétrica",
    "agua": "Água",
    "gases": "Gases medicinais",
    "temperatura": "Temperatura",
    "umidade": "Umidade",
    "vibracao": "Vibração",
    "pressao": "Pressão",
}
