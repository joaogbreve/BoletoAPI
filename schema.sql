-- Instituições parceiras
CREATE TABLE IF NOT EXISTS instituicoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_fantasia TEXT NOT NULL,
    cnpj TEXT NOT NULL UNIQUE,
    token_acesso TEXT NOT NULL UNIQUE,
    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS boletos (
    id TEXT PRIMARY KEY, -- UUID
    codigo_barras TEXT NOT NULL UNIQUE,
    data_vencimento TEXT NOT NULL,
    valor REAL NOT NULL,
    valor_pago REAL, -- pode ser NULL se não pago ainda
    status TEXT NOT NULL DEFAULT 'pendente', -- pendente, pago, cancelado
    data_pagamento DATETIME, -- NULL até o pagamento ser confirmado
    pagador_cpf_cnpj TEXT,
    pagador_nome TEXT,
    pagador_cad_cpf_cnpj TEXT NOT NULL,
    pagador_cad_nome TEXT NOT NULL,
    beneficiario_nome TEXT NOT NULL,
    beneficiario_cnpj TEXT NOT NULL,
    id_instituicao INTEGER NOT NULL,
    aceita_termos BOOLEAN NOT NULL DEFAULT 0,
    telefone TEXT,
    notificar_telefone BOOLEAN NOT NULL DEFAULT 0,
    email TEXT,
    notificar_email BOOLEAN NOT NULL DEFAULT 0,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_instituicao) REFERENCES instituicoes(id)
);

-- Tentativas suspeitas: registros de pagamentos com divergências
CREATE TABLE IF NOT EXISTS tentativas_suspeitas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_barras TEXT NOT NULL,
    cnpj_benficiado TEXT,
    nome_benficiado TEXT,
    pagador_cpf_cnpj TEXT,
    pagador_nome TEXT,
    pagador_cad_cpf_cnpj TEXT NOT NULL,
    pagador_cad_nome TEXT NOT NULL,
    motivo TEXT NOT NULL,
    detalhes TEXT,
    data_verificacao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Blacklist: CPFs/CNPJs bloqueados por fraudes confirmadas
CREATE TABLE IF NOT EXISTS blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_barras TEXT NOT NULL,
    nome TEXT NOT NULL,
    cnpj_benficiado TEXT NOT NULL,
    pagador_cad_cpf_cnpj TEXT NOT NULL,
    motivo TEXT,
    data_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Log geral para auditoria
CREATE TABLE IF NOT EXISTS log_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acao TEXT NOT NULL,
    origem TEXT,
    dados TEXT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
);
