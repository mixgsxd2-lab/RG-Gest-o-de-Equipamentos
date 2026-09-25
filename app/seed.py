"""Dados FICTÍCIOS de DEMONSTRAÇÃO.

Nenhuma informação real de pacientes, colaboradores ou fornecedores é usada.
Os chamados são gerados pelo próprio motor de fluxo (services.tickets), de modo
que histórico, custos, SLA e baixas de estoque ficam coerentes entre si.
"""
import math
import random
from datetime import date, datetime, timedelta

from .extensions import db
from .models import (Asset, Contract, CostEntry, PreventivePlan, Product, Sector, Sensor, SensorReading,
                     StockMovement, Supplier, Team, Technician, User)
from .services import tickets as svc

DEMO_PASSWORD = "123456"

SECTORS = [
    ("Pronto-Socorro", "Bloco A", "Térreo", "CC-110"),
    ("UTI Adulto", "Bloco B", "2º andar", "CC-210"),
    ("UTI Neonatal", "Bloco B", "3º andar", "CC-220"),
    ("Centro Cirúrgico", "Bloco B", "1º andar", "CC-230"),
    ("CME - Central de Material e Esterilização", "Bloco B", "1º andar", "CC-240"),
    ("Diagnóstico por Imagem", "Bloco A", "Térreo", "CC-310"),
    ("Laboratório de Análises Clínicas", "Bloco A", "1º andar", "CC-320"),
    ("Hemodiálise", "Bloco C", "Térreo", "CC-330"),
    ("Internação Clínica", "Bloco C", "2º andar", "CC-410"),
    ("Internação Cirúrgica", "Bloco C", "3º andar", "CC-420"),
    ("Maternidade", "Bloco D", "1º andar", "CC-430"),
    ("Farmácia Hospitalar", "Bloco A", "Subsolo", "CC-510"),
    ("Nutrição e Dietética", "Bloco D", "Térreo", "CC-520"),
    ("Lavanderia", "Anexo", "Térreo", "CC-530"),
    ("Ambulatório", "Bloco D", "Térreo", "CC-440"),
    ("Administração", "Bloco A", "4º andar", "CC-900"),
    ("Utilidades / Casa de Máquinas", "Anexo", "Subsolo", "CC-950"),
]

TEAMS = [
    ("Engenharia Clínica", "Equipamentos médico-hospitalares", "#0f6cbd"),
    ("Manutenção Predial", "Civil, pintura, marcenaria e serralheria", "#8a5cf6"),
    ("Elétrica", "Instalações elétricas, geradores e nobreaks", "#f59e0b"),
    ("Hidráulica", "Água, esgoto, vapor e osmose", "#0ea5e9"),
    ("Climatização", "Ar-condicionado, chillers e câmaras frias", "#14b8a6"),
    ("Gases Medicinais", "Oxigênio, ar comprimido, vácuo e redes", "#ef4444"),
]

SUPPLIERS = [
    ("medtech", "MedTech Sul Serviços Hospitalares (fictício)", "00.111.222/0001-01", "Engenharia Clínica",
     "Paula Ramos", 4.6),
    ("clima", "ClimaPampa Refrigeração (fictício)", "00.222.333/0001-02", "Climatização", "Jorge Alves", 4.1),
    ("gasmed", "GasVida Gases Medicinais (fictício)", "00.333.444/0001-03", "Gases Medicinais", "Renata Dias",
     4.8),
    ("eletro", "EletroForte Engenharia (fictício)", "00.444.555/0001-04", "Elétrica", "André Barros", 3.7),
    ("elevador", "Elevadores Horizonte (fictício)", "00.555.666/0001-05", "Elevadores", "Silvia Rocha", 3.9),
    ("imagem", "ImagemCare Assistência Técnica (fictício)", "00.666.777/0001-06", "Diagnóstico por Imagem",
     "Tiago Martins", 4.3),
    ("hidro", "HidroServ Soluções Hidráulicas (fictício)", "00.777.888/0001-07", "Hidráulica", "Luana Pires",
     4.0),
    ("distrib", "Distribuidora Hospitalar Lagoa (fictício)", "00.888.999/0001-08", "Materiais e peças",
     "Fábio Teles", 4.4),
]

USERS = [
    # username, nome, perfil, setor, equipe
    ("admin", "Administrador do Sistema", "admin", "Administração", None),
    ("gestor", "Carlos Menezes", "gestor", "Utilidades / Casa de Máquinas", None),
    ("operador", "Rafael Souza", "operador", "Utilidades / Casa de Máquinas", "Engenharia Clínica"),
    ("usuario", "Juliana Castro", "solicitante", "UTI Adulto", None),
    ("estoque", "Marcos Lima", "estoque", "Utilidades / Casa de Máquinas", None),
    ("diretoria", "Helena Prado", "diretoria", "Administração", None),
    ("tecnico.eletrica", "Bruno Carvalho", "operador", "Utilidades / Casa de Máquinas", "Elétrica"),
    ("tecnico.predial", "Sérgio Nunes", "operador", "Utilidades / Casa de Máquinas", "Manutenção Predial"),
    ("tecnico.clima", "Diego Farias", "operador", "Utilidades / Casa de Máquinas", "Climatização"),
    ("tecnico.hidraulica", "Leandro Moraes", "operador", "Utilidades / Casa de Máquinas", "Hidráulica"),
    ("tecnico.gases", "Patrícia Vieira", "operador", "Utilidades / Casa de Máquinas", "Gases Medicinais"),
    ("tecnico.clinica2", "Camila Rocha", "operador", "Utilidades / Casa de Máquinas", "Engenharia Clínica"),
    ("ps.enfermagem", "Fernanda Luz", "solicitante", "Pronto-Socorro", None),
    ("cc.coordenacao", "Roberto Tavares", "solicitante", "Centro Cirúrgico", None),
    ("lab.coordenacao", "Aline Figueiredo", "solicitante", "Laboratório de Análises Clínicas", None),
    ("imagem.coordenacao", "Márcio Queiroz", "solicitante", "Diagnóstico por Imagem", None),
    ("nutricao", "Beatriz Moura", "solicitante", "Nutrição e Dietética", None),
    ("hemodialise", "Gustavo Pacheco", "solicitante", "Hemodiálise", None),
    ("internacao", "Sandra Oliveira", "solicitante", "Internação Clínica", None),
    ("neonatal", "Larissa Mendes", "solicitante", "UTI Neonatal", None),
    ("cme", "Otávio Ribeiro", "solicitante", "CME - Central de Material e Esterilização", None),
    ("farmacia", "Vanessa Freitas", "solicitante", "Farmácia Hospitalar", None),
]

TECHNICIANS = [
    # nome, especialidade, equipe, username, fornecedor, turno, R$/h
    ("Rafael Souza", "Técnico em Eletrônica / Equipamentos Médicos", "Engenharia Clínica", "operador", None,
     "Diurno", 62.0),
    ("Camila Rocha", "Engenheira Clínica", "Engenharia Clínica", "tecnico.clinica2", None, "Diurno", 85.0),
    ("Bruno Carvalho", "Eletricista de Alta e Baixa Tensão", "Elétrica", "tecnico.eletrica", None, "12x36", 55.0),
    ("Sérgio Nunes", "Oficial de Manutenção Predial", "Manutenção Predial", "tecnico.predial", None, "Diurno",
     42.0),
    ("Diego Farias", "Técnico em Refrigeração", "Climatização", "tecnico.clima", None, "Diurno", 58.0),
    ("Leandro Moraes", "Encanador / Bombeiro Hidráulico", "Hidráulica", "tecnico.hidraulica", None, "12x36",
     45.0),
    ("Patrícia Vieira", "Técnica em Gases Medicinais", "Gases Medicinais", "tecnico.gases", None, "Diurno", 60.0),
    ("Anderson Luz", "Pintor / Marceneiro", "Manutenção Predial", None, None, "Diurno", 38.0),
    ("Eduardo Brum", "Técnico de Campo (terceiro)", "Engenharia Clínica", None, "medtech", "Sob demanda", 110.0),
    ("Mateus Kich", "Técnico de Refrigeração (terceiro)", "Climatização", None, "clima", "Sob demanda", 95.0),
]

# tag, nome, categoria, tipo, setor, local, fabricante, modelo, anos de uso, custo, vida útil,
# criticidade, status, fornecedor, equipe responsável
ASSETS = [
    ("RG-EQ-0001", "Ventilador Pulmonar", "Suporte à vida", "Equipamento", "UTI Adulto", "Leito 01",
     "VitaMed", "VM-900", 4.5, 98000, 10, "Crítica", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0002", "Ventilador Pulmonar", "Suporte à vida", "Equipamento", "UTI Adulto", "Leito 05",
     "VitaMed", "VM-900", 4.5, 98000, 10, "Crítica", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0003", "Ventilador Pulmonar Neonatal", "Suporte à vida", "Equipamento", "UTI Neonatal", "Box 02",
     "NeoCare", "NV-300", 7.2, 120000, 10, "Crítica", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0004", "Monitor Multiparamétrico", "Monitoração", "Equipamento", "UTI Adulto", "Leito 03",
     "CardioTech", "MX-12", 6.0, 32000, 8, "Alta", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0005", "Monitor Multiparamétrico", "Monitoração", "Equipamento", "Pronto-Socorro", "Sala Vermelha",
     "CardioTech", "MX-12", 8.5, 32000, 8, "Alta", "Em manutenção", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0006", "Desfibrilador / Cardioversor", "Suporte à vida", "Equipamento", "Pronto-Socorro",
     "Sala Vermelha", "CardioTech", "DF-50", 5.0, 28000, 8, "Crítica", "Operacional", "medtech",
     "Engenharia Clínica"),
    ("RG-EQ-0007", "Bomba de Infusão", "Infusão", "Equipamento", "Internação Clínica", "Posto de Enfermagem 2A",
     "InfusaPro", "BI-20", 3.0, 7800, 7, "Alta", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0008", "Bomba de Infusão", "Infusão", "Equipamento", "UTI Adulto", "Leito 07", "InfusaPro", "BI-20",
     3.0, 7800, 7, "Alta", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0009", "Incubadora Neonatal", "Neonatologia", "Equipamento", "UTI Neonatal", "Box 04", "NeoCare",
     "IN-70", 9.5, 45000, 10, "Crítica", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0010", "Mesa Cirúrgica Elétrica", "Centro cirúrgico", "Equipamento", "Centro Cirúrgico", "Sala 02",
     "SurgiLine", "MC-4000", 11.0, 85000, 15, "Alta", "Operacional", None, "Engenharia Clínica"),
    ("RG-EQ-0011", "Foco Cirúrgico LED", "Centro cirúrgico", "Equipamento", "Centro Cirúrgico", "Sala 01",
     "SurgiLine", "FL-LED2", 4.0, 62000, 12, "Alta", "Operacional", None, "Engenharia Clínica"),
    ("RG-EQ-0012", "Bisturi Elétrico", "Centro cirúrgico", "Equipamento", "Centro Cirúrgico", "Sala 03",
     "ElectroSurg", "BE-300", 6.5, 26000, 10, "Alta", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0013", "Autoclave a Vapor 360L", "Esterilização", "Equipamento",
     "CME - Central de Material e Esterilização", "Área de esterilização", "EsteriMax", "AV-360", 9.0, 210000,
     15, "Crítica", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0014", "Lavadora Termodesinfectora", "Esterilização", "Equipamento",
     "CME - Central de Material e Esterilização", "Expurgo", "EsteriMax", "LT-200", 6.0, 150000, 12, "Alta",
     "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0015", "Tomógrafo Computadorizado 64 canais", "Diagnóstico por imagem", "Equipamento",
     "Diagnóstico por Imagem", "Sala TC", "ImagemPro", "CT-64", 5.5, 2400000, 10, "Crítica", "Operacional",
     "imagem", "Engenharia Clínica"),
    ("RG-EQ-0016", "Aparelho de Raio-X Digital", "Diagnóstico por imagem", "Equipamento",
     "Diagnóstico por Imagem", "Sala RX 1", "ImagemPro", "DR-500", 8.0, 680000, 10, "Alta", "Operacional",
     "imagem", "Engenharia Clínica"),
    ("RG-EQ-0017", "Ultrassom Portátil", "Diagnóstico por imagem", "Equipamento", "Pronto-Socorro",
     "Sala de Emergência", "ImagemPro", "US-P7", 2.0, 145000, 8, "Média", "Operacional", "imagem",
     "Engenharia Clínica"),
    ("RG-EQ-0018", "Máquina de Hemodiálise", "Hemodiálise", "Equipamento", "Hemodiálise", "Poltrona 03",
     "RenalTec", "HD-5008", 6.0, 95000, 10, "Crítica", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0019", "Máquina de Hemodiálise", "Hemodiálise", "Equipamento", "Hemodiálise", "Poltrona 07",
     "RenalTec", "HD-5008", 9.8, 95000, 10, "Crítica", "Inoperante", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0020", "Analisador Bioquímico", "Laboratório", "Equipamento", "Laboratório de Análises Clínicas",
     "Bioquímica", "LabSys", "AB-800", 4.0, 380000, 8, "Alta", "Operacional", "medtech", "Engenharia Clínica"),
    ("RG-EQ-0021", "Centrífuga Refrigerada", "Laboratório", "Equipamento", "Laboratório de Análises Clínicas",
     "Triagem", "LabSys", "CR-24", 7.5, 38000, 10, "Média", "Operacional", None, "Engenharia Clínica"),
    ("RG-EQ-0022", "Refrigerador de Medicamentos", "Refrigeração", "Equipamento", "Farmácia Hospitalar",
     "Rede de frio", "FrioMed", "RM-450", 5.0, 18000, 10, "Alta", "Operacional", None, "Climatização"),
    ("RG-EQ-0023", "Cardiotocógrafo", "Monitoração", "Equipamento", "Maternidade", "Pré-parto", "CardioTech",
     "CTG-2", 3.5, 24000, 8, "Média", "Reserva", "medtech", "Engenharia Clínica"),
    ("RG-IN-0001", "Grupo Gerador Diesel 500 kVA", "Energia", "Estrutura/Instalação",
     "Utilidades / Casa de Máquinas", "Casa do gerador", "PowerGen", "GD-500", 12.0, 420000, 20, "Crítica",
     "Operacional", "eletro", "Elétrica"),
    ("RG-IN-0002", "Nobreak 80 kVA - Centro Cirúrgico", "Energia", "Estrutura/Instalação", "Centro Cirúrgico",
     "Sala técnica", "VoltSafe", "UPS-80", 6.0, 160000, 10, "Crítica", "Operacional", "eletro", "Elétrica"),
    ("RG-IN-0003", "Quadro Geral de Baixa Tensão (QGBT)", "Energia", "Estrutura/Instalação",
     "Utilidades / Casa de Máquinas", "Subestação", "VoltSafe", "QGBT-3000A", 15.0, 290000, 25, "Crítica",
     "Operacional", "eletro", "Elétrica"),
    ("RG-IN-0004", "Chiller 150 TR", "Climatização", "Estrutura/Instalação", "Utilidades / Casa de Máquinas",
     "Cobertura Bloco B", "FrioMax", "CH-150", 10.5, 780000, 20, "Crítica", "Operacional", "clima",
     "Climatização"),
    ("RG-IN-0005", "Fan Coil - Centro Cirúrgico", "Climatização", "Estrutura/Instalação", "Centro Cirúrgico",
     "Entreforro sala 01-03", "FrioMax", "FC-20", 10.5, 65000, 15, "Alta", "Operacional", "clima",
     "Climatização"),
    ("RG-IN-0006", "Câmara Fria de Alimentos", "Refrigeração", "Estrutura/Instalação", "Nutrição e Dietética",
     "Estoque de perecíveis", "FrioMax", "CF-12", 8.0, 90000, 15, "Alta", "Operacional", "clima",
     "Climatização"),
    ("RG-IN-0007", "Central de Oxigênio Líquido (tanque criogênico)", "Gases medicinais",
     "Estrutura/Instalação", "Utilidades / Casa de Máquinas", "Área externa - central de gases", "GasVida",
     "TQ-10000", 7.0, 350000, 20, "Crítica", "Operacional", "gasmed", "Gases Medicinais"),
    ("RG-IN-0008", "Central de Vácuo Clínico", "Gases medicinais", "Estrutura/Instalação",
     "Utilidades / Casa de Máquinas", "Central de gases", "GasVida", "VC-2B", 9.0, 140000, 15, "Crítica",
     "Operacional", "gasmed", "Gases Medicinais"),
    ("RG-IN-0009", "Compressor de Ar Medicinal", "Gases medicinais", "Estrutura/Instalação",
     "Utilidades / Casa de Máquinas", "Central de gases", "GasVida", "AC-30", 13.5, 120000, 15, "Crítica",
     "Operacional", "gasmed", "Gases Medicinais"),
    ("RG-IN-0010", "Sistema de Osmose Reversa", "Água tratada", "Estrutura/Instalação", "Hemodiálise",
     "Sala de tratamento de água", "AquaPura", "OR-2000", 5.0, 185000, 12, "Crítica", "Operacional", "hidro",
     "Hidráulica"),
    ("RG-IN-0011", "Conjunto Motobomba de Recalque", "Água e esgoto", "Estrutura/Instalação",
     "Utilidades / Casa de Máquinas", "Casa de bombas", "HidroMax", "MB-25", 11.0, 42000, 12, "Alta",
     "Operacional", "hidro", "Hidráulica"),
    ("RG-IN-0012", "Elevador de Macas 01", "Transporte vertical", "Estrutura/Instalação", "Internação Clínica",
     "Hall Bloco C", "Horizonte", "EM-1600", 14.0, 380000, 25, "Crítica", "Operacional", "elevador",
     "Manutenção Predial"),
    ("RG-IN-0013", "Lavadora Extratora 100 kg", "Lavanderia", "Estrutura/Instalação", "Lavanderia",
     "Área suja/limpa", "LavTec", "LE-100", 10.0, 175000, 15, "Alta", "Operacional", None, "Manutenção Predial"),
    ("RG-IN-0014", "Cobertura e Impermeabilização Bloco C", "Estrutura predial", "Estrutura/Instalação",
     "Internação Clínica", "Telhado Bloco C", "—", "—", 16.0, 260000, 25, "Média", "Operacional", None,
     "Manutenção Predial"),
]

PRODUCTS = [
    # código, nome, categoria, unidade, qtd inicial, mínimo, custo, local, fornecedor
    ("MAT-0001", "Sensor de fluxo para ventilador", "Peças eng. clínica", "un", 6, 2, 1850.0, "A1-01", "medtech"),
    ("MAT-0002", "Cabo de ECG 5 vias", "Peças eng. clínica", "un", 14, 5, 390.0, "A1-02", "distrib"),
    ("MAT-0003", "Sensor de SpO2 adulto", "Peças eng. clínica", "un", 12, 6, 280.0, "A1-03", "distrib"),
    ("MAT-0004", "Bateria 12V 7Ah", "Elétrica", "un", 20, 8, 145.0, "B2-01", "distrib"),
    ("MAT-0005", "Kit de manutenção preventiva p/ ventilador", "Peças eng. clínica", "kit", 5, 2, 2400.0,
     "A1-04", "medtech"),
    ("MAT-0006", "Lâmpada LED tubular 18W", "Elétrica", "un", 120, 40, 22.0, "B2-02", "distrib"),
    ("MAT-0007", "Disjuntor tripolar 63A", "Elétrica", "un", 8, 3, 210.0, "B2-03", "eletro"),
    ("MAT-0008", "Cabo flexível 4mm² (rolo 100m)", "Elétrica", "rolo", 6, 2, 480.0, "B2-04", "distrib"),
    ("MAT-0009", "Filtro de ar G4 (fan coil)", "Climatização", "un", 40, 20, 65.0, "C3-01", "clima"),
    ("MAT-0010", "Filtro HEPA H14", "Climatização", "un", 6, 4, 1450.0, "C3-02", "clima"),
    ("MAT-0011", "Gás refrigerante R-410A (cilindro 11,3kg)", "Climatização", "cil", 4, 2, 890.0, "C3-03",
     "clima"),
    ("MAT-0012", "Correia em V A-48", "Climatização", "un", 10, 4, 58.0, "C3-04", "distrib"),
    ("MAT-0013", "Registro de gaveta 3/4\"", "Hidráulica", "un", 15, 5, 78.0, "D4-01", "distrib"),
    ("MAT-0014", "Válvula de descarga", "Hidráulica", "un", 10, 4, 185.0, "D4-02", "distrib"),
    ("MAT-0015", "Membrana de osmose reversa 8\"", "Hidráulica", "un", 3, 2, 3200.0, "D4-03", "hidro"),
    ("MAT-0016", "Tubo PVC 50mm (barra 6m)", "Hidráulica", "br", 30, 10, 62.0, "D4-04", "distrib"),
    ("MAT-0017", "Válvula reguladora de O2", "Gases medicinais", "un", 8, 4, 520.0, "E5-01", "gasmed"),
    ("MAT-0018", "Fluxômetro de O2 0-15 L/min", "Gases medicinais", "un", 20, 10, 240.0, "E5-02", "gasmed"),
    ("MAT-0019", "Kit de vedação (O-rings) p/ régua de gases", "Gases medicinais", "kit", 12, 5, 95.0, "E5-03",
     "gasmed"),
    ("MAT-0020", "Tinta acrílica antibacteriana 18L", "Predial", "lata", 12, 4, 420.0, "F6-01", "distrib"),
    ("MAT-0021", "Fechadura de porta com maçaneta", "Predial", "un", 15, 5, 135.0, "F6-02", "distrib"),
    ("MAT-0022", "Rodízio para cama hospitalar", "Predial", "un", 24, 12, 88.0, "F6-03", "distrib"),
    ("MAT-0023", "Selante de silicone neutro", "Predial", "tb", 30, 10, 28.0, "F6-04", "distrib"),
    ("MAT-0024", "Resistência elétrica p/ autoclave", "Peças eng. clínica", "un", 2, 2, 1680.0, "A1-05",
     "medtech"),
    ("MAT-0025", "Óleo lubrificante p/ compressor (5L)", "Gases medicinais", "gl", 6, 3, 310.0, "E5-04",
     "gasmed"),
]

# Modelos de chamados: (equipe, título, descrição, tipos, prioridades, ativos possíveis (tags) ou setores,
#                       diagnóstico, solução, causa, materiais [(código, qtd)], horas, custo terceiro)
TEMPLATES = [
    ("Engenharia Clínica", "Ventilador pulmonar com alarme de falha no sensor de fluxo",
     "Equipamento apresentando alarme intermitente de 'falha sensor de fluxo' durante uso.",
     ["Corretiva"], ["Urgente", "Alta"], ["RG-EQ-0001", "RG-EQ-0002", "RG-EQ-0003"],
     "Sensor de fluxo descalibrado/danificado.", "Substituído sensor de fluxo e realizado teste de desempenho.",
     "Desgaste de componente", [("MAT-0001", 1)], (2, 4), 0),
    ("Engenharia Clínica", "Monitor multiparamétrico sem leitura de SpO2",
     "Monitor não apresenta curva de oximetria em nenhum paciente.",
     ["Corretiva"], ["Alta", "Média"], ["RG-EQ-0004", "RG-EQ-0005"],
     "Cabo/sensor de SpO2 rompido.", "Substituído sensor de SpO2 e testado com simulador.",
     "Mau uso / dano físico", [("MAT-0003", 1)], (1, 2), 0),
    ("Engenharia Clínica", "Bomba de infusão com oclusão falsa",
     "Bomba dispara alarme de oclusão sem obstrução aparente na linha.",
     ["Corretiva"], ["Alta", "Média"], ["RG-EQ-0007", "RG-EQ-0008"],
     "Sensor de pressão com sujeira acumulada.", "Limpeza do mecanismo e recalibração do sensor de pressão.",
     "Falta de limpeza", [], (1, 2), 0),
    ("Engenharia Clínica", "Calibração anual de equipamentos de monitoração",
     "Calibração e teste de segurança elétrica conforme cronograma.",
     ["Calibração"], ["Média", "Baixa"], ["RG-EQ-0004", "RG-EQ-0005", "RG-EQ-0006", "RG-EQ-0023"],
     "Equipamento dentro das tolerâncias após ajuste.", "Calibração realizada com analisador; laudo emitido.",
     None, [], (2, 3), 0),
    ("Engenharia Clínica", "Autoclave não atinge temperatura de esterilização",
     "Ciclo abortado por não atingir 134 °C. CME operando com uma autoclave apenas.",
     ["Corretiva", "Emergencial"], ["Urgente"], ["RG-EQ-0013"],
     "Resistência elétrica do gerador de vapor queimada.", "Substituída resistência e realizado teste Bowie-Dick.",
     "Desgaste de componente", [("MAT-0024", 1)], (3, 6), 0),
    ("Engenharia Clínica", "Máquina de hemodiálise com alarme de condutividade",
     "Alarme de condutividade fora da faixa ao iniciar sessão.",
     ["Corretiva"], ["Urgente", "Alta"], ["RG-EQ-0018", "RG-EQ-0019"],
     "Célula de condutividade com incrustação.", "Desincrustação química e calibração da célula de condutividade.",
     "Qualidade da água", [], (2, 4), 0),
    ("Engenharia Clínica", "Falha no detector do tomógrafo",
     "Artefatos em anel nas imagens. Exames suspensos.",
     ["Corretiva"], ["Urgente"], ["RG-EQ-0015"],
     "Módulo do detector com falha.", "Acionado fabricante; substituição do módulo sob contrato.",
     "Falha eletrônica", [], (4, 8), 18500),
    ("Engenharia Clínica", "Instalação de novo ultrassom portátil",
     "Recebimento, testes de aceitação e treinamento da equipe do PS.",
     ["Instalação"], ["Média"], ["RG-EQ-0017"],
     "Equipamento conforme especificação.", "Instalado, testado e realizado treinamento com 12 colaboradores.",
     None, [], (3, 5), 0),
    ("Engenharia Clínica", "Incubadora neonatal com oscilação de temperatura",
     "Temperatura interna oscilando ±1,5 °C do setpoint.",
     ["Corretiva", "Preditiva"], ["Urgente", "Alta"], ["RG-EQ-0009"],
     "Sensor de temperatura da cúpula com mau contato.", "Refeito conector do sensor e validado com termômetro padrão.",
     "Falha eletrônica", [], (2, 3), 0),
    ("Elétrica", "Queda de disjuntor no quadro do posto de enfermagem",
     "Tomadas do posto de enfermagem sem energia após desarme do disjuntor.",
     ["Corretiva", "Emergencial"], ["Alta", "Urgente"], ["sector:Internação Clínica", "sector:Maternidade",
                                                        "sector:Internação Cirúrgica"],
     "Sobrecarga no circuito por uso de equipamentos adicionais.", "Redistribuídas cargas e substituído disjuntor.",
     "Sobrecarga elétrica", [("MAT-0007", 1)], (1, 3), 0),
    ("Elétrica", "Troca de lâmpadas queimadas no corredor",
     "Várias lâmpadas queimadas no corredor principal.",
     ["Corretiva"], ["Baixa", "Média"], ["sector:Ambulatório", "sector:Internação Clínica", "sector:Pronto-Socorro",
                                         "sector:Administração"],
     "Lâmpadas no fim da vida útil.", "Substituídas lâmpadas por LED tubular.", "Fim de vida útil",
     [("MAT-0006", 6)], (1, 2), 0),
    ("Elétrica", "Teste mensal do grupo gerador com carga",
     "Rotina de teste do gerador com transferência de carga.",
     ["Inspeção", "Preventiva"], ["Média"], ["RG-IN-0001"],
     "Parâmetros normais.", "Teste realizado por 30 min com carga; níveis verificados.", None, [], (2, 2), 0),
    ("Elétrica", "Nobreak do centro cirúrgico em bypass",
     "Nobreak entrou em modo bypass e emitiu alarme de bateria.",
     ["Corretiva", "Emergencial"], ["Urgente"], ["RG-IN-0002"],
     "Banco de baterias degradado.", "Substituídas baterias com falha e realizada descarga controlada.",
     "Fim de vida útil", [("MAT-0004", 8)], (3, 5), 0),
    ("Elétrica", "Termografia do QGBT",
     "Inspeção termográfica semestral dos barramentos e conexões.",
     ["Preditiva", "Inspeção"], ["Média"], ["RG-IN-0003"],
     "Ponto quente em conexão do circuito 14.", "Reaperto de conexões e nova termografia sem anomalias.",
     "Conexão frouxa", [], (3, 4), 2400),
    ("Climatização", "Ar-condicionado não refrigera",
     "Sala muito quente, equipamento ligado sem refrigerar.",
     ["Corretiva"], ["Média", "Alta"], ["sector:Administração", "sector:Farmácia Hospitalar", "sector:Ambulatório",
                                        "sector:Laboratório de Análises Clínicas"],
     "Vazamento de gás refrigerante.", "Localizado e corrigido vazamento; recarga de gás.", "Vazamento",
     [("MAT-0011", 1)], (2, 4), 0),
    ("Climatização", "Troca de filtros dos fan coils do centro cirúrgico",
     "Troca programada de filtros G4 e verificação de pressão diferencial.",
     ["Preventiva"], ["Média"], ["RG-IN-0005"],
     "Filtros saturados conforme esperado.", "Filtros substituídos; pressão diferencial dentro do especificado.",
     None, [("MAT-0009", 6)], (2, 3), 0),
    ("Climatização", "Chiller com vibração acima do normal",
     "Monitoramento indicou aumento de vibração no compressor 2.",
     ["Preditiva"], ["Alta"], ["RG-IN-0004"],
     "Desalinhamento e desgaste de correias.", "Alinhamento, troca de correias e balanceamento.",
     "Desgaste de componente", [("MAT-0012", 4)], (4, 6), 3200),
    ("Climatização", "Câmara fria com temperatura elevada",
     "Câmara fria da nutrição marcando 9 °C (limite 5 °C).",
     ["Corretiva", "Emergencial"], ["Urgente"], ["RG-IN-0006"],
     "Evaporador congelado por falha no degelo.", "Substituído termostato de degelo e realizado degelo manual.",
     "Falha eletrônica", [], (2, 4), 0),
    ("Climatização", "Refrigerador de medicamentos fora da faixa",
     "Termômetro registrou 10 °C na rede de frio da farmácia.",
     ["Corretiva"], ["Urgente", "Alta"], ["RG-EQ-0022"],
     "Borracha de vedação da porta danificada.", "Substituída gaxeta e ajustado termostato.", "Desgaste de componente",
     [], (1, 2), 0),
    ("Hidráulica", "Vazamento em banheiro de enfermaria",
     "Vazamento no sifão da pia com água no piso.",
     ["Corretiva"], ["Média", "Alta"], ["sector:Internação Clínica", "sector:Internação Cirúrgica",
                                        "sector:Maternidade", "sector:Pronto-Socorro"],
     "Sifão trincado.", "Substituído sifão e vedação.", "Desgaste de componente", [("MAT-0023", 1)], (1, 2), 0),
    ("Hidráulica", "Válvula de descarga com vazamento contínuo",
     "Descarga do sanitário não para de escoar.",
     ["Corretiva"], ["Baixa", "Média"], ["sector:Ambulatório", "sector:Administração", "sector:Pronto-Socorro"],
     "Reparo interno da válvula desgastado.", "Substituída válvula de descarga.", "Desgaste de componente",
     [("MAT-0014", 1)], (1, 2), 0),
    ("Hidráulica", "Troca de membranas da osmose reversa",
     "Condutividade do permeado acima de 10 µS/cm.",
     ["Preventiva", "Corretiva"], ["Alta"], ["RG-IN-0010"],
     "Membranas saturadas.", "Substituída membrana e sanitização do loop; análise de água coletada.",
     "Qualidade da água", [("MAT-0015", 1)], (4, 6), 1800),
    ("Hidráulica", "Motobomba de recalque ruidosa",
     "Ruído metálico na bomba 2 de recalque.",
     ["Corretiva", "Preditiva"], ["Alta"], ["RG-IN-0011"],
     "Rolamento danificado.", "Substituídos rolamentos e selo mecânico por empresa terceirizada.",
     "Desgaste de componente", [], (3, 5), 2200),
    ("Gases Medicinais", "Vazamento em régua de gases",
     "Ruído de vazamento na saída de O2 da régua do leito.",
     ["Corretiva", "Emergencial"], ["Urgente", "Alta"], ["sector:UTI Adulto", "sector:Pronto-Socorro",
                                                        "sector:UTI Neonatal", "sector:Internação Clínica"],
     "O-ring da válvula de engate ressecado.", "Substituído kit de vedação e teste de estanqueidade.",
     "Desgaste de componente", [("MAT-0019", 1)], (1, 2), 0),
    ("Gases Medicinais", "Fluxômetro de oxigênio com defeito",
     "Fluxômetro não regula vazão.",
     ["Corretiva"], ["Alta", "Média"], ["sector:Internação Cirúrgica", "sector:Maternidade", "sector:UTI Adulto"],
     "Mecanismo interno travado.", "Substituído fluxômetro.", "Desgaste de componente", [("MAT-0018", 1)], (1, 1), 0),
    ("Gases Medicinais", "Inspeção da central de oxigênio",
     "Inspeção de níveis, pressões e válvulas de alívio da central.",
     ["Inspeção"], ["Média"], ["RG-IN-0007"],
     "Parâmetros normais.", "Inspeção concluída; registro no livro da central.", None, [], (1, 2), 0),
    ("Gases Medicinais", "Compressor de ar medicinal com temperatura alta",
     "Alarme de temperatura no compressor 1.",
     ["Corretiva"], ["Urgente", "Alta"], ["RG-IN-0009"],
     "Óleo degradado e radiador obstruído.", "Troca de óleo e limpeza do radiador.", "Falta de limpeza",
     [("MAT-0025", 1)], (2, 4), 0),
    ("Manutenção Predial", "Porta da enfermaria com fechadura quebrada",
     "Fechadura não trava; porta abre sozinha.",
     ["Corretiva"], ["Baixa", "Média"], ["sector:Internação Clínica", "sector:Internação Cirúrgica",
                                         "sector:Maternidade", "sector:Ambulatório"],
     "Miolo da fechadura quebrado.", "Substituída fechadura.", "Mau uso / dano físico", [("MAT-0021", 1)], (1, 1), 0),
    ("Manutenção Predial", "Pintura de quarto após alta",
     "Paredes com manchas e descascamento; necessário pintar antes de nova internação.",
     ["Corretiva"], ["Baixa"], ["sector:Internação Clínica", "sector:Internação Cirúrgica", "sector:Maternidade"],
     "Desgaste natural da pintura.", "Aplicadas duas demãos de tinta antibacteriana.", "Desgaste natural",
     [("MAT-0020", 1)], (4, 8), 0),
    ("Manutenção Predial", "Infiltração no teto da enfermaria",
     "Mancha de umidade e gotejamento no forro após chuva.",
     ["Corretiva"], ["Alta", "Média"], ["RG-IN-0014"],
     "Manta asfáltica danificada na cobertura.", "Reparo da impermeabilização e troca de placas de forro.",
     "Intempéries", [("MAT-0023", 3)], (6, 10), 4500),
    ("Manutenção Predial", "Elevador de macas parado entre andares",
     "Elevador parou entre 1º e 2º andar; sem passageiros.",
     ["Corretiva", "Emergencial"], ["Urgente"], ["RG-IN-0012"],
     "Falha no inversor de frequência.", "Empresa contratada substituiu placa do inversor.", "Falha eletrônica",
     [], (2, 5), 3900),
    ("Manutenção Predial", "Troca de rodízios de camas hospitalares",
     "Camas com rodízios travando e sem freio.",
     ["Corretiva"], ["Baixa", "Média"], ["sector:Internação Clínica", "sector:Internação Cirúrgica"],
     "Rodízios desgastados.", "Substituídos 4 rodízios.", "Desgaste de componente", [("MAT-0022", 4)], (1, 2), 0),
    ("Manutenção Predial", "Lavadora extratora com desbalanceamento",
     "Máquina vibra excessivamente na centrifugação.",
     ["Corretiva"], ["Alta"], ["RG-IN-0013"],
     "Amortecedores gastos.", "Substituídos amortecedores e nivelada a máquina.", "Desgaste de componente",
     [], (3, 4), 1200),
]

PLANS = [
    # nome, ativo, equipe, técnico, fornecedor, tipo, frequência (dias), dias até o vencimento, horas, checklist
    ("Preventiva trimestral ventilador pulmonar RG-EQ-0001", "RG-EQ-0001", "Engenharia Clínica", "Rafael Souza",
     None, "Preventiva", 90, -4, 3, "Troca de filtros\nTeste de vazamento\nVerificação de alarmes\nTeste de desempenho"),
    ("Preventiva trimestral ventilador pulmonar RG-EQ-0002", "RG-EQ-0002", "Engenharia Clínica", "Rafael Souza",
     None, "Preventiva", 90, 12, 3, "Troca de filtros\nTeste de vazamento\nVerificação de alarmes"),
    ("Calibração anual desfibrilador", "RG-EQ-0006", "Engenharia Clínica", "Camila Rocha", None, "Calibração",
     365, 3, 2, "Teste de energia entregue\nTeste de sincronismo\nSegurança elétrica"),
    ("Preventiva semestral incubadora neonatal", "RG-EQ-0009", "Engenharia Clínica", "Camila Rocha", None,
     "Preventiva", 180, 20, 2, "Limpeza\nCalibração de temperatura e umidade\nTeste de alarmes"),
    ("Validação mensal da autoclave (Bowie-Dick)", "RG-EQ-0013", "Engenharia Clínica", "Rafael Souza", None,
     "Inspeção", 30, 1, 1, "Teste Bowie-Dick\nVerificação de vedação da porta\nRegistro de ciclo"),
    ("Preventiva semestral tomógrafo (contrato)", "RG-EQ-0015", "Engenharia Clínica", None, "imagem",
     "Preventiva", 180, 45, 8, "Calibração de detectores\nVerificação do tubo\nQualidade de imagem"),
    ("Desinfecção e preventiva máquinas de hemodiálise", "RG-EQ-0018", "Engenharia Clínica", "Camila Rocha",
     None, "Preventiva", 60, -9, 3, "Desinfecção térmica\nTroca de filtros\nCalibração condutividade"),
    ("Teste mensal do gerador com carga", "RG-IN-0001", "Elétrica", "Bruno Carvalho", None, "Inspeção", 30, 6,
     2, "Nível de óleo e combustível\nTransferência automática\n30 min em carga"),
    ("Termografia semestral QGBT", "RG-IN-0003", "Elétrica", None, "eletro", "Preditiva", 180, 60, 4,
     "Termografia de barramentos\nReaperto se necessário"),
    ("Manutenção do banco de baterias do nobreak", "RG-IN-0002", "Elétrica", "Bruno Carvalho", None,
     "Preventiva", 90, -15, 3, "Medição de tensão das baterias\nTeste de autonomia"),
    ("Limpeza e troca de filtros fan coil CC", "RG-IN-0005", "Climatização", "Diego Farias", None, "Preventiva",
     30, 2, 2, "Troca filtros G4\nMedição de pressão diferencial\nLimpeza de bandeja"),
    ("Preventiva mensal chiller", "RG-IN-0004", "Climatização", None, "clima", "Preventiva", 30, 14, 6,
     "Análise de vibração\nPressões de trabalho\nLimpeza de condensadores"),
    ("Sanitização mensal da osmose reversa", "RG-IN-0010", "Hidráulica", "Leandro Moraes", None, "Preventiva",
     30, -2, 4, "Sanitização química\nAnálise de condutividade\nColeta microbiológica"),
    ("Inspeção semanal da central de gases", "RG-IN-0007", "Gases Medicinais", "Patrícia Vieira", None,
     "Inspeção", 7, 0, 1, "Níveis e pressões\nVálvulas de alívio\nAlarmes da central"),
    ("Troca de óleo do compressor de ar medicinal", "RG-IN-0009", "Gases Medicinais", "Patrícia Vieira", None,
     "Preventiva", 120, 33, 2, "Troca de óleo\nTroca de filtros\nDreno de condensado"),
    ("Manutenção mensal do elevador de macas", "RG-IN-0012", "Manutenção Predial", None, "elevador",
     "Preventiva", 30, 9, 3, "Freios\nCabos de tração\nDispositivos de segurança"),
]

SENSORS = [
    # código, nome, tipo, unidade, ativo, setor, min, max, base, amplitude, deriva final
    ("EN-QGBT-01", "Demanda elétrica QGBT", "energia", "kW", "RG-IN-0003", None, 50, 620, 380, 120, 0),
    ("EN-GER-01", "Nível de combustível do gerador", "energia", "%", "RG-IN-0001", None, 40, 100, 86, 2, 0),
    ("AG-RES-01", "Nível do reservatório superior", "agua", "%", "RG-IN-0011", None, 30, 100, 72, 12, 0),
    ("AG-CONS-01", "Vazão de água - entrada geral", "agua", "m³/h", None, "Utilidades / Casa de Máquinas", 0, 25,
     9, 5, 0),
    ("AG-OR-01", "Condutividade do permeado - osmose", "agua", "µS/cm", "RG-IN-0010", None, 0, 10, 4.2, 0.8, 0),
    ("GS-O2-01", "Pressão da rede de oxigênio", "gases", "bar", "RG-IN-0007", None, 3.5, 4.5, 4.0, 0.08, 0),
    ("GS-O2-02", "Nível do tanque criogênico de O2", "gases", "%", "RG-IN-0007", None, 25, 100, 64, 3, -20),
    ("GS-VAC-01", "Vácuo clínico - pressão", "gases", "mmHg", "RG-IN-0008", None, -700, -450, -560, 15, 0),
    ("GS-AR-01", "Pressão do ar medicinal", "gases", "bar", "RG-IN-0009", None, 3.5, 4.5, 4.1, 0.07, 0),
    ("TP-FAR-01", "Temperatura refrigerador de medicamentos", "temperatura", "°C", "RG-EQ-0022", None, 2, 8, 5,
     0.6, 3.6),
    ("TP-CF-01", "Temperatura câmara fria (nutrição)", "temperatura", "°C", "RG-IN-0006", None, 0, 5, 2.5, 0.7, 0),
    ("TP-CC-01", "Temperatura sala cirúrgica 01", "temperatura", "°C", None, "Centro Cirúrgico", 18, 22, 20.5,
     0.5, 0),
    ("UM-CC-01", "Umidade sala cirúrgica 01", "umidade", "%", None, "Centro Cirúrgico", 40, 60, 52, 4, 0),
    ("VB-CH-01", "Vibração compressor 2 do chiller", "vibracao", "mm/s", "RG-IN-0004", None, 0, 7.1, 3.2, 0.5,
     4.8),
]


def _dt(days_ago, hour=None, rnd=None):
    rnd = rnd or random
    base = datetime.now().replace(second=0, microsecond=0) - timedelta(days=days_ago)
    if hour is None:
        hour = rnd.choice([7, 8, 8, 9, 10, 10, 11, 13, 14, 14, 15, 16, 17, 19, 21, 2])
    return base.replace(hour=hour, minute=rnd.choice([0, 5, 12, 20, 33, 41, 48, 55]))


def seed_demo(seed=2026):
    rnd = random.Random(seed)
    now = datetime.now().replace(second=0, microsecond=0)
    today = date.today()

    sectors = {}
    for name, building, floor, cc in SECTORS:
        sectors[name] = Sector(name=name, building=building, floor=floor, cost_center=cc)
        db.session.add(sectors[name])
    teams = {}
    for name, desc, color in TEAMS:
        teams[name] = Team(name=name, description=desc, color=color)
        db.session.add(teams[name])

    suppliers = {}
    for key, name, cnpj, cat, contact, rating in SUPPLIERS:
        slug = key + ".demo"
        suppliers[key] = Supplier(name=name, cnpj=cnpj, category=cat, contact_name=contact,
                                  phone=f"(53) 3200-{rnd.randint(1000, 9999)}",
                                  email=f"contato@{slug}.invalid", rating=rating)
        db.session.add(suppliers[key])

    users = {}
    for username, name, role, sector, team in USERS:
        u = User(username=username, name=name, role=role, sector=sectors.get(sector), team=teams.get(team),
                 email=f"{username}@demo.hospitalriogrande.invalid")
        u.set_password(DEMO_PASSWORD)
        users[username] = u
        db.session.add(u)

    techs = {}
    for name, spec, team, username, supplier, shift, rate in TECHNICIANS:
        t = Technician(name=name, specialty=spec, team=teams[team], user=users.get(username),
                       supplier=suppliers.get(supplier), shift=shift, hourly_rate=rate,
                       registration=f"RG{rnd.randint(10000, 99999)}", phone=f"(53) 99{rnd.randint(100, 999)}-{rnd.randint(1000, 9999)}")
        techs[name] = t
        db.session.add(t)

    contracts = [
        ("CT-2024-011", "medtech", "Engenharia Clínica", "Manutenção preventiva e corretiva de equipamentos médicos",
         -600, 130, 18500, 4, 24),
        ("CT-2025-003", "clima", "Climatização", "Manutenção do sistema de climatização central (PMOC)",
         -420, 310, 12800, 4, 12),
        ("CT-2023-021", "gasmed", "Gases Medicinais", "Fornecimento de O2 líquido e manutenção da central de gases",
         -900, 45, 22000, 2, 6),
        ("CT-2025-014", "elevador", "Manutenção Predial", "Manutenção mensal de elevadores", -250, 480, 4600, 2, 8),
        ("CT-2024-030", "imagem", "Engenharia Clínica", "Contrato full service tomógrafo e raio-X", -300, 430,
         27500, 4, 48),
        ("CT-2025-022", "hidro", "Hidráulica", "Manutenção do sistema de tratamento de água (osmose)", -180, 185,
         6200, 6, 24),
        ("CT-2023-008", "eletro", "Elétrica", "Manutenção de subestação, gerador e nobreaks", -1100, -20, 9800, 4,
         12),
    ]
    contract_objs = []
    for number, sup, team, scope, start_off, end_off, value, resp, res in contracts:
        c = Contract(number=number, supplier=suppliers[sup], team=teams[team], scope=scope,
                     start_date=today + timedelta(days=start_off), end_date=today + timedelta(days=end_off),
                     monthly_value=value, sla_response_hours=resp, sla_resolution_hours=res)
        contract_objs.append(c)
        db.session.add(c)

    assets = {}
    for (tag, name, cat, kind, sector, loc, manuf, model, years, cost, life, crit, status, sup, _team) in ASSETS:
        acq = today - timedelta(days=int(years * 365.25))
        a = Asset(tag=tag, name=name, category=cat, kind=kind, sector=sectors[sector], location=loc,
                  manufacturer=manuf, model=model, serial_number=f"SN{rnd.randint(100000, 999999)}",
                  acquisition_date=acq, acquisition_cost=cost, useful_life_years=life,
                  residual_value=round(cost * 0.1, 2), status=status, criticality=crit,
                  supplier=suppliers.get(sup),
                  warranty_until=acq + timedelta(days=int(365 * 2.2)) if years < 2.5 else None,
                  notes="Ativo fictício de demonstração.")
        assets[tag] = a
        db.session.add(a)

    products = {}
    stock_start = now - timedelta(days=200)
    for code, name, cat, unit, qty, min_q, cost, loc, sup in PRODUCTS:
        p = Product(code=code, name=name, category=cat, unit=unit, quantity=qty * 3, min_stock=min_q,
                    unit_cost=cost, storage_location=loc, supplier=suppliers.get(sup))
        products[code] = p
        db.session.add(p)
        db.session.add(StockMovement(product=p, kind="entrada", quantity=qty * 3, unit_cost=cost,
                                     supplier=suppliers.get(sup), user=users["estoque"], document="NF-DEMO",
                                     note="Saldo inicial (demonstração)", created_at=stock_start))
    db.session.flush()

    plans = {}
    for (name, tag, team, tech, sup, mtype, freq, due_in, hours, checklist) in PLANS:
        p = PreventivePlan(name=name, asset=assets[tag], team=teams[team], technician=techs.get(tech),
                           supplier=suppliers.get(sup), maintenance_type=mtype, frequency_days=freq,
                           next_due=today + timedelta(days=due_in), estimated_hours=hours, checklist=checklist,
                           last_done=today + timedelta(days=due_in - freq))
        plans[name] = (p, due_in)
        db.session.add(p)
    db.session.flush()

    gestor = users["gestor"]
    requesters_by_sector = {}
    for u in users.values():
        if u.role == "solicitante" and u.sector:
            requesters_by_sector.setdefault(u.sector.name, []).append(u)
    fallback_requesters = [users["usuario"], users["gestor"], users["ps.enfermagem"], users["internacao"]]

    def tech_for(team_name, external=False):
        opts = [t for t in techs.values() if t.team.name == team_name and (t.supplier is not None) == external]
        if not opts:
            opts = [t for t in techs.values() if t.team.name == team_name]
        return rnd.choice(opts)

    def actor(tech):
        return tech.user if tech.user is not None else gestor

    def run_ticket(tpl, created, final_status, target_ref=None, plan=None, force_violation=False,
                   mtype=None, prio=None):
        """Cria um chamado e o conduz pelo fluxo até ``final_status``."""
        (team, title, desc, types, prios, targets, diag, solution, cause, mats, hours, third) = tpl
        mtype = plan.maintenance_type if plan else (mtype or rnd.choice(types))
        prio = prio or rnd.choice(prios)
        target = target_ref or rnd.choice(targets)
        asset = None
        if target.startswith("sector:"):
            sector = sectors[target.split(":", 1)[1]]
        else:
            asset = assets[target]
            sector = asset.sector
        req_pool = requesters_by_sector.get(sector.name) or fallback_requesters
        requester = gestor if plan else rnd.choice(req_pool)
        data = {"title": title if not plan else plan.ticket_title,
                "description": desc if not plan else (plan.checklist or desc),
                "maintenance_type": mtype, "priority": prio,
                "criticality": asset.criticality if asset else rnd.choice(["Baixa", "Média", "Alta"]),
                "team_id": teams[team].id, "asset_id": asset.id if asset else None, "sector_id": sector.id,
                "location": asset.location if asset else rnd.choice(["Quarto 204", "Quarto 212", "Corredor principal",
                                                                     "Sala 3", "Banheiro coletivo", "Posto de enfermagem",
                                                                     "Sala de espera", "Expurgo"]),
                "preventive_plan_id": plan.id if plan else None}
        t = svc.create_ticket(data, requester, at=created)
        db.session.flush()
        sla = t.sla_hours
        # linha do tempo proporcional ao SLA
        if force_violation:
            total = sla * rnd.uniform(1.3, 2.6)
        else:
            total = sla * rnd.uniform(0.25, 0.92)
        waits = rnd.random() < 0.22 and final_status not in ("aberto", "recebido", "aceito")
        work_h = rnd.uniform(*hours)
        steps = {
            "recebido": created + timedelta(hours=total * 0.05),
            "aceito": created + timedelta(hours=total * 0.12),
            "em_execucao": created + timedelta(hours=total * 0.2),
            "finalizado": created + timedelta(hours=total),
        }
        steps["encerrado"] = steps["finalizado"] + timedelta(hours=rnd.uniform(2, 40))
        order = ["aberto", "recebido", "aceito", "em_execucao", "aguardando", "finalizado", "encerrado", "cancelado"]
        limit = now - timedelta(minutes=10)
        # comprime a linha do tempo se ultrapassar o momento atual
        last_needed = {"aberto": created, "recebido": steps["recebido"], "aceito": steps["aceito"],
                       "em_execucao": steps["em_execucao"], "aguardando": steps["em_execucao"],
                       "finalizado": steps["finalizado"], "encerrado": steps["encerrado"],
                       "cancelado": steps["recebido"]}[final_status]
        if last_needed > limit and last_needed > created:
            factor = max(0.05, (limit - created) / (last_needed - created))
            for k in steps:
                steps[k] = created + (steps[k] - created) * factor
        target_idx = order.index(final_status)
        external = third > 0 and rnd.random() < 0.6
        tech = plan.technician if plan and plan.technician else \
            tech_for(team, external=external or bool(plan and plan.supplier))

        if final_status == "cancelado":
            svc.apply_action(t, "receive", gestor, {}, at=steps["recebido"])
            svc.apply_action(t, "cancel", gestor, {"note": rnd.choice(
                ["Chamado duplicado", "Problema resolvido pelo próprio setor", "Aberto por engano"])},
                at=steps["recebido"] + timedelta(minutes=20))
            return t
        if target_idx >= 1:
            svc.apply_action(t, "receive", gestor, {}, at=steps["recebido"])
            if rnd.random() < 0.6 or tech.user is None:
                svc.apply_action(t, "assign", gestor, {"technician_id": tech.id},
                                 at=steps["recebido"] + timedelta(minutes=5))
        if target_idx >= 2:
            if tech.user is not None:
                svc.apply_action(t, "accept", tech.user, {}, at=steps["aceito"])
            else:
                svc.apply_action(t, "accept", gestor, {"technician_id": tech.id}, at=steps["aceito"])
        if target_idx >= 3:
            who = actor(tech)
            svc.apply_action(t, "start", who, {}, at=steps["em_execucao"])
            span = (steps["finalizado"] - steps["em_execucao"])
            mat_at = steps["em_execucao"] + span * 0.3
            for code, qty in mats:
                if rnd.random() < 0.85 and products[code].quantity >= qty:
                    svc.add_material(t, who, {"product_id": products[code].id, "quantity": qty}, at=mat_at)
            if waits or final_status == "aguardando":
                reason = "Terceiro" if (third or external) else rnd.choice(["Material", "Material", "Terceiro"])
                wait_at = steps["em_execucao"] + span * 0.35
                sup = tech.supplier or (asset.supplier if asset else None)
                svc.apply_action(t, "wait", who, {"waiting_reason": reason,
                                                  "supplier_id": sup.id if (sup and reason == "Terceiro") else None,
                                                  "note": "Aguardando peça do fornecedor" if reason == "Material"
                                                  else "Acionada assistência técnica externa"}, at=wait_at)
                if final_status != "aguardando":
                    svc.apply_action(t, "resume", who, {"note": "Material/serviço recebido"},
                                     at=steps["em_execucao"] + span * 0.8)
            # apontamento de horas (limitado à janela de execução)
            start = steps["em_execucao"]
            end = min(start + timedelta(hours=work_h), steps["finalizado"] if target_idx >= 5 else limit)
            if end > start + timedelta(minutes=10) and target_idx >= 5:
                svc.add_worklog(t, who, {"started_at": start, "ended_at": end, "technician_id": tech.id,
                                         "description": "Diagnóstico e execução do serviço"},
                                at=end)
        if target_idx >= 5:
            who = actor(tech)
            sup = tech.supplier or (asset.supplier if asset and third else None)
            svc.apply_action(t, "finish", who, {
                "diagnosis": diag, "solution": solution, "failure_cause": cause,
                "observations": rnd.choice(["", "Equipamento liberado para uso.", "Orientada a equipe do setor.",
                                            "Recomendada substituição na próxima revisão."]),
                "third_party_cost": round(third * rnd.uniform(0.8, 1.2), 2) if third else 0,
                "supplier_id": sup.id if (sup and third) else None,
            }, at=steps["finalizado"])
        if target_idx >= 6:
            svc.apply_action(t, "close", t.requester if t.requester.role == "solicitante" else gestor,
                             {"closing_notes": rnd.choice(["Serviço conferido pelo setor.", "Atendimento satisfatório.",
                                                           "Equipamento testado e aprovado.", "Encerrado pela gestão."]),
                              "satisfaction": rnd.choice([3, 4, 4, 5, 5, 5])}, at=steps["encerrado"])
        return t

    # ---- Chamados históricos e atuais -------------------------------------------------
    history_specs = []
    for i in range(100):
        days_ago = rnd.uniform(15, 238)
        r = rnd.random()
        final = "encerrado" if r < 0.84 else "finalizado" if r < 0.92 else "cancelado" if r < 0.96 else "encerrado"
        history_specs.append((days_ago, final, rnd.random() < 0.14))
    recent_status = (["aberto"] * 4 + ["recebido"] * 3 + ["aceito"] * 3 + ["em_execucao"] * 4 +
                     ["aguardando"] * 3 + ["finalizado"] * 4 + ["encerrado"] * 5)
    for final in recent_status:
        days_ago = rnd.uniform(0.1, 12) if final in ("aberto", "recebido", "aceito") else rnd.uniform(0.5, 14)
        history_specs.append((days_ago, final, rnd.random() < 0.18))
    history_specs.sort(key=lambda s: -s[0])

    # (data de abertura, argumentos) — executados em ordem cronológica para numeração coerente
    jobs = []
    for days_ago, final, violate in history_specs:
        created = _dt(int(days_ago), rnd=rnd) - timedelta(minutes=rnd.randint(0, 50))
        if created > now - timedelta(minutes=30):
            created = now - timedelta(hours=rnd.uniform(1, 5))
        tpl = rnd.choice(TEMPLATES)
        mtype, prio = rnd.choice(tpl[3]), rnd.choice(tpl[4])
        if final in ("aberto", "recebido", "aceito", "em_execucao") and not violate:
            # chamados em andamento abertos recentemente, dentro do prazo de SLA
            created = now - timedelta(hours=svc.sla_hours_for(prio, mtype) * rnd.uniform(0.1, 0.7))
        jobs.append((created, dict(tpl=tpl, final_status=final, force_violation=violate, mtype=mtype,
                                   prio=prio)))

    # ---- Execuções de preventivas (histórico) --------------------------------------------
    tpl_by_asset = {}
    for tpl in TEMPLATES:
        for target in tpl[5]:
            tpl_by_asset.setdefault(target, tpl)
    plan_last = {}
    for name, (plan, due_in) in plans.items():
        tag = plan.asset.tag
        base_tpl = tpl_by_asset.get(tag) or TEMPLATES[3]
        tpl = (plan.team.name, plan.name, plan.checklist, [plan.maintenance_type], ["Média"], [tag],
               "Equipamento dentro dos parâmetros.", "Plano executado conforme checklist.", None,
               base_tpl[9][:1] if plan.maintenance_type == "Preventiva" else [],
               (plan.estimated_hours, plan.estimated_hours + 1), 0)
        last = today + timedelta(days=due_in - plan.frequency_days)
        executions = []
        d = last
        while d >= today - timedelta(days=235) and len(executions) < 8:
            if d < today:
                executions.append(d)
            d -= timedelta(days=plan.frequency_days)
        plan_last[plan.id] = max(executions) if executions else None
        for ex in executions:
            created = datetime.combine(ex, datetime.min.time()).replace(hour=8) - timedelta(days=1)
            jobs.append((created, dict(tpl=tpl, final_status="encerrado", target_ref=tag, plan=plan,
                                       force_violation=rnd.random() < 0.08)))

    jobs.sort(key=lambda j: j[0])
    for created, kwargs in jobs:
        run_ticket(created=created, **kwargs)

    # restaura o calendário planejado (algumas preventivas atrasadas, outras próximas)
    for name, (plan, due_in) in plans.items():
        plan.next_due = today + timedelta(days=due_in)
        plan.last_done = plan_last.get(plan.id)

    # OS preventiva gerada e ainda em aberto para um plano atrasado
    overdue_plan = plans["Manutenção do banco de baterias do nobreak"][0]
    t = svc.create_ticket({"title": overdue_plan.ticket_title, "description": overdue_plan.checklist,
                           "maintenance_type": "Preventiva", "priority": "Alta", "criticality": "Crítica",
                           "team_id": overdue_plan.team_id, "asset_id": overdue_plan.asset_id,
                           "preventive_plan_id": overdue_plan.id}, gestor, at=now - timedelta(days=2))
    svc.apply_action(t, "assign", gestor, {"technician_id": overdue_plan.technician_id},
                     at=now - timedelta(days=2, hours=-1))

    # ---- Custos de contratos e investimentos --------------------------------------------
    for c in contract_objs:
        m = date(today.year, today.month, 1)
        for _ in range(9):
            if c.start_date <= m <= c.end_date:
                db.session.add(CostEntry(category="Contrato", amount=c.monthly_value, date=m, contract=c,
                                         supplier=c.supplier, team=c.team,
                                         description=f"Mensalidade {c.number} — {m:%m/%Y}"))
            m = (m - timedelta(days=1)).replace(day=1)
    investments = [
        ("Aquisição de ultrassom portátil para o PS", 145000, 70, "Pronto-Socorro", "RG-EQ-0017"),
        ("Retrofit de iluminação LED - Bloco C", 38500, 120, "Internação Clínica", None),
        ("Reforma da sala de tratamento de água da hemodiálise", 62000, 40, "Hemodiálise", "RG-IN-0010"),
        ("Substituição de 10 bombas de infusão", 78000, 15, "UTI Adulto", None),
    ]
    for desc, amount, days_ago, sector, tag in investments:
        db.session.add(CostEntry(category="Investimento", description=desc, amount=amount,
                                 date=today - timedelta(days=days_ago), sector=sectors[sector],
                                 asset=assets.get(tag)))

    # ---- Estoque: reposições e níveis finais ----------------------------------------------
    for code, name, cat, unit, qty, min_q, cost, loc, sup in PRODUCTS:
        p = products[code]
        target = qty if code not in ("MAT-0010", "MAT-0015", "MAT-0024", "MAT-0019", "MAT-0004") else \
            max(0, min_q - rnd.choice([0, 1, 1, 2]))
        if p.quantity > target:
            diff = p.quantity - target
            p.quantity = target
            db.session.add(StockMovement(product=p, kind="saida", quantity=diff, unit_cost=p.unit_cost,
                                         user=users["estoque"], note="Requisições diversas (demonstração)",
                                         created_at=now - timedelta(days=rnd.randint(3, 60))))
        elif p.quantity < target:
            diff = target - p.quantity
            p.quantity = target
            db.session.add(StockMovement(product=p, kind="entrada", quantity=diff, unit_cost=p.unit_cost,
                                         supplier=p.supplier, user=users["estoque"], document="NF-DEMO",
                                         note="Reposição (demonstração)",
                                         created_at=now - timedelta(days=rnd.randint(3, 60))))

    # ---- Situação final dos ativos -------------------------------------------------------
    db.session.flush()
    for row in ASSETS:
        assets[row[0]].status = row[12]
    for t in svc.Ticket.query.filter(svc.Ticket.status.in_(["em_execucao", "aguardando"])).all():
        if t.asset and t.asset.status == "Operacional" and t.maintenance_type in ("Corretiva", "Emergencial"):
            t.asset.status = "Em manutenção"

    # ---- Sensores IoT e leituras dos últimos 7 dias ---------------------------------------
    for code, name, kind, unit, tag, sector, mn, mx, base, amp, drift in SENSORS:
        asset = assets.get(tag)
        s = Sensor(code=code, name=name, kind=kind, unit=unit, asset=asset,
                   sector=asset.sector if asset else sectors.get(sector), min_value=mn, max_value=mx,
                   protocol=rnd.choice(["MQTT", "Modbus TCP", "HTTP"]))
        db.session.add(s)
        db.session.flush()
        points = 7 * 24 * 2
        value = base
        for i in range(points):
            ts = now - timedelta(minutes=30 * (points - i))
            hour = ts.hour + ts.minute / 60
            daily = math.sin((hour - 8) / 24 * 2 * math.pi)
            value = base + amp * (0.6 * daily + 0.4 * rnd.uniform(-1, 1)) + drift * (i / points) ** 3
            db.session.add(SensorReading(sensor_id=s.id, value=round(value, 2), recorded_at=ts))
        s.last_value, s.last_reading_at = round(value, 2), now - timedelta(minutes=30)

    db.session.commit()
