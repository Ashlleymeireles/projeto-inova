from flask import Flask, render_template, request, jsonify, g
import sqlite3
from datetime import datetime
import os
import json
import random

app = Flask(__name__)
app.config['DATABASE'] = 'database.db'
db_path = os.getenv('SQLITE_PATH', 'database.db')  # pega variável ou usa default

conn = sqlite3.connect(db_path)
print(f"Conectado ao banco SQLite em {db_path}")



# =============================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# =============================================

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# =============================================
# ROTAS PRINCIPAIS
# =============================================

@app.route('/')
def index():
    return render_template('index.html')

# =============================================
# API - USUÁRIOS
# =============================================

@app.route('/api/usuarios', methods=['GET', 'POST'])
def usuarios():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        try:
            db.execute(
                'INSERT INTO usuarios (nome, email, telefone) VALUES (?, ?, ?)',
                [data['nome'], data['email'], data['telefone']]
            )
            db.commit()
            return jsonify({"message": "Usuário cadastrado com sucesso!"}), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": "Email já cadastrado!"}), 400
    
    usuarios = db.execute('SELECT * FROM usuarios').fetchall()
    return jsonify([dict(u) for u in usuarios])

# =============================================
# API - LIVROS
# =============================================

@app.route('/api/livros', methods=['GET', 'POST'])
def livros():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        try:
            db.execute('''
                INSERT INTO livros 
                (titulo, autor, categoria, cidade, biblioteca, secao, localizacao, descricao) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                data['titulo'], data['autor'], data['categoria'],
                data['cidade'], data['biblioteca'], data['secao'],
                data.get('localizacao', ''), data['descricao']
            ])
            db.commit()
            return jsonify({"message": "Livro cadastrado com sucesso!"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    livros = db.execute('SELECT * FROM livros').fetchall()
    if not livros:
        return jsonify([])  # Retorna array vazio se não houver livros
    return jsonify([dict(l) for l in livros])

@app.route('/api/livros/<int:id>', methods=['DELETE'])
def deletar_livro(id):
    db = get_db()
    try:
        db.execute('DELETE FROM livros WHERE id = ?', [id])
        db.commit()
        return jsonify({"message": "Livro removido com sucesso!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# =============================================
# API - EMPRÉSTIMOS
# =============================================

@app.route('/api/emprestimos', methods=['GET', 'POST'])
def emprestimos():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        try:
            db.execute('''
                INSERT INTO emprestimos 
                (usuario_id, livro_id, data_emprestimo, data_devolucao, status, multa) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', [
                data['usuario_id'], data['livro_id'],
                data['data_emprestimo'], data['data_devolucao'],
                'Pendente', 0
            ])
            db.commit()
            return jsonify({
                "message": "Empréstimo cadastrado com sucesso!",
                "alerta": "Atenção! Será cobrada uma taxa de R$ 3,00 por dia após o prazo de devolução."
            }), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    emprestimos = db.execute('''
        SELECT e.id, u.nome as usuario, l.titulo as livro, 
               e.data_emprestimo, e.data_devolucao, e.status, e.multa
        FROM emprestimos e
        JOIN usuarios u ON e.usuario_id = u.id
        JOIN livros l ON e.livro_id = l.id
    ''').fetchall()
    
    return jsonify([dict(e) for e in emprestimos])

@app.route('/api/emprestimos/<int:id>/devolver', methods=['PUT'])
def devolver_emprestimo(id):
    db = get_db()
    try:
        emprestimo = db.execute('SELECT * FROM emprestimos WHERE id = ?', [id]).fetchone()
        if not emprestimo:
            return jsonify({"error": "Empréstimo não encontrado"}), 404
        
        data_devolucao = datetime.strptime(emprestimo['data_devolucao'], '%Y-%m-%d').date()
        hoje = datetime.now().date()
        multa = max(0, (hoje - data_devolucao).days) * 3 if hoje > data_devolucao else 0
        
        db.execute(
            'UPDATE emprestimos SET status = ?, multa = ? WHERE id = ?',
            ['Devolvido', multa, id]
        )
        db.commit()
        
        return jsonify({
            "message": "Livro devolvido com sucesso!",
            "multa": multa
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/emprestimos/<int:id>', methods=['DELETE'])
def excluir_emprestimo(id):
    db = get_db()
    try:
        db.execute('DELETE FROM emprestimos WHERE id = ?', [id])
        db.commit()
        return jsonify({"message": "Empréstimo excluído com sucesso!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# =============================================
# API - BUSCA INTELIGENTE
# =============================================

@app.route('/api/busca', methods=['POST'])
def busca_inteligente():
    try:
        descricao = request.json.get('descricao', '').lower()
        db = get_db()
        
        # Busca por termos relevantes
        livros = db.execute('''
            SELECT * FROM livros 
            WHERE LOWER(titulo) LIKE ? OR 
                  LOWER(autor) LIKE ? OR 
                  LOWER(descricao) LIKE ? OR 
                  LOWER(categoria) LIKE ? OR 
                  LOWER(localizacao) LIKE ?
        ''', [f'%{descricao}%'] * 5).fetchall()
        
        if not livros:
            return jsonify([])
        
        return jsonify([dict(l) for l in livros])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
# API - CHAT INTELIGENTE
# =============================================

RESPOSTAS_CHAT = {
    "saudacao": ["Olá! Como posso ajudar?", "Oi! Em que posso ajudar hoje?"],
    "emprestimo": [
        "Para fazer um empréstimo, vá para a aba 'Empréstimos' e preencha os dados.",
        "O prazo padrão para empréstimos é de 15 dias."
    ],
    "livro": [
        "Você pode cadastrar novos livros na aba 'Acervo'.",
        "Experimente nossa Busca Inteligente para encontrar livros!"
    ],
    "devolucao": [
        "O prazo de devolução é de 15 dias com multa de R$3,00 por dia de atraso.",
        "Para devolver, clique no botão 'Devolver' na tabela de relatórios."
    ],
    "padrao": [
        "Desculpe, não entendi. Pode reformular?",
        "Interessante! Sobre qual aspecto você gostaria de saber mais?"
    ]
}

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        mensagem = request.json.get('message', '').lower()
        
        if any(palavra in mensagem for palavra in ["ola", "oi", "olá", "bom dia"]):
            resposta = random.choice(RESPOSTAS_CHAT["saudacao"])
        elif any(palavra in mensagem for palavra in ["emprestimo", "emprestar"]):
            resposta = random.choice(RESPOSTAS_CHAT["emprestimo"])
        elif any(palavra in mensagem for palavra in ["livro", "acervo"]):
            resposta = random.choice(RESPOSTAS_CHAT["livro"])
        elif any(palavra in mensagem for palavra in ["devolver", "devolucao", "multa"]):
            resposta = random.choice(RESPOSTAS_CHAT["devolucao"])
        else:
            resposta = random.choice(RESPOSTAS_CHAT["padrao"])
        
        return jsonify({"response": resposta})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
# INICIALIZAÇÃO
# =============================================

PORT = int(os.getenv('PORT', 5000))

if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        init_db()
    app.run(host='0.0.0.0', port=PORT)