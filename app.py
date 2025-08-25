from flask import Flask, render_template, request, redirect, flash, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'segredo' 


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'reservas.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn



def criar_tabela():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nome TEXT NOT NULL,
            laboratorio TEXT NOT NULL,
            sala TEXT NOT NULL,
            data TEXT NOT NULL,
            horario_inicio TEXT NOT NULL,
            horario_fim TEXT NOT NULL,
            usuario_id INTEGER NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

criar_tabela()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id, nome, senha FROM usuarios WHERE email = ?', (email,))
            user = c.fetchone()

        if not user:
            flash('Email não cadastrado no sistema.')
            return render_template('login.html')
        elif not check_password_hash(user[2], senha):
            flash('Email ou senha incorretos.')
            return render_template('login.html')
        else:
            session['usuario_id'] = user[0]
            session['nome'] = user[1]
            return redirect('/menu')

    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        senha_hash = generate_password_hash(senha)

        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)', (nome, email, senha_hash))
                conn.commit()
        except sqlite3.IntegrityError:
            flash('Email já cadastrado.')
            return render_template('cadastro.html')
        flash('Cadastro realizado com sucesso. Faça login!')
        return redirect('/login')

    return render_template('cadastro.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/menu')
@login_required
def menu():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT nome, laboratorio, sala, data, horario_inicio, horario_fim
            FROM reservas
            WHERE usuario_id = ?
            ORDER BY data, horario_inicio
        ''', (session['usuario_id'],))
        reservas = c.fetchall()
    return render_template('menu.html', nome=session['nome'], reservas=reservas)


@app.route('/ver_reservas')
def ver_reservas():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT nome, laboratorio, sala, data, horario_inicio, horario_fim
            FROM reservas
            ORDER BY data, horario_inicio
        ''')
        reservas = c.fetchall()
    return render_template('ver_reserva.html', reservas=reservas)

@app.route('/reserva', methods=['GET', 'POST'])
@login_required
def reserva():
    if request.method == 'POST':
        nome = session['nome']
        laboratorio = request.form.get('laboratorio', '')
        sala = request.form.get('sala', '')
        data = request.form.get('data', '')
        horario_inicio = request.form.get('horario_inicio', '')
        horario_fim = request.form.get('horario_fim', '')

        erros = []

        try:
            data_formatada = datetime.strptime(data, '%Y-%m-%d')
            if data_formatada.date() < datetime.now().date():
                erros.append("A data não pode estar no passado.")
        except ValueError:
            erros.append("Data inválida.")

        try:
            nova_inicio = datetime.strptime(f"{data} {horario_inicio}", '%Y-%m-%d %H:%M')
            nova_fim = datetime.strptime(f"{data} {horario_fim}", '%Y-%m-%d %H:%M')
            if nova_fim <= nova_inicio:
                erros.append("Horário final deve ser depois do horário inicial.")
        except ValueError:
            erros.append("Horários inválidos.")

        if erros:
            for erro in erros:
                flash(erro)
            return render_template('reserva.html')

        with get_db_connection() as conn:
            c = conn.cursor()

            c.execute('''
                SELECT COUNT(*) FROM reservas
                WHERE usuario_id = ? AND strftime('%Y-%m', data) = ?
            ''', (session['usuario_id'], data_formatada.strftime('%Y-%m')))
            total_reservas = c.fetchone()[0]
            if total_reservas >= 3:
                flash("Você já fez 3 reservas neste mês.")
                return render_template('reserva.html')

            c.execute('''
                SELECT * FROM reservas
                WHERE laboratorio = ? AND sala = ? AND data = ?
            ''', (laboratorio, sala, data))
            reservas_existentes = c.fetchall()

            for r in reservas_existentes:
                r_inicio = datetime.strptime(r['horario_inicio'], '%H:%M')
                r_fim = datetime.strptime(r['horario_fim'], '%H:%M') + timedelta(minutes=5)
                if (nova_inicio.time() < r_fim.time()) and (nova_fim.time() > r_inicio.time()):
                    flash("Conflito com outra reserva.")
                    return render_template('reserva.html')

            c.execute('''
                INSERT INTO reservas (nome, laboratorio, sala, data, horario_inicio, horario_fim, usuario_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nome, laboratorio, sala, data, horario_inicio, horario_fim, session['usuario_id']))
            conn.commit()

        flash("Reserva realizada com sucesso!")
        return redirect('/menu')

    return render_template('reserva.html')

@app.route('/suporte')
def suporte():
    logado = 'usuario_id' in session
    return render_template('suporte.html', logado=logado)


@app.route('/limpar_banco')
def limpar_banco():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM reservas')
        c.execute('DELETE FROM usuarios')
        conn.commit()
    return 'Banco de dados limpo com sucesso!'


if __name__ == '__main__':
    app.run(debug=True)
