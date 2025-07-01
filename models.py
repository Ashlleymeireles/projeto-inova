from datetime import date

class Livro:
    def __init__(self, titulo, autor, categoria, cidade, biblioteca, secao, localizacao, descricao):
        self.titulo = titulo
        self.autor = autor
        self.categoria = categoria
        self.cidade = cidade
        self.biblioteca = biblioteca
        self.secao = secao
        self.localizacao = localizacao
        self.descricao = descricao

class Usuario:
    def __init__(self, nome, email, telefone):
        self.nome = nome
        self.email = email
        self.telefone = telefone

class Emprestimo:
    def __init__(self, usuario_id, livro_id, data_emprestimo, data_devolucao, status, multa):
        self.usuario_id = usuario_id
        self.livro_id = livro_id
        self.data_emprestimo = data_emprestimo
        self.data_devolucao = data_devolucao
        self.status = status
        self.multa = multa