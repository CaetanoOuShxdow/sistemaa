import sqlite3

def adicionar_coluna_usuario_id():
    conn = sqlite3.connect('reservas.db')
    cursor = conn.cursor()

    # Verifica se a coluna já existe
    cursor.execute("PRAGMA table_info(reservas)")
    colunas = [info[1] for info in cursor.fetchall()]
    
    if 'usuario_id' not in colunas:
        print("Adicionando coluna 'usuario_id' na tabela 'reservas'...")
        cursor.execute('ALTER TABLE reservas ADD COLUMN usuario_id INTEGER')
        conn.commit()
        print("Coluna adicionada com sucesso.")
    else:
        print("A coluna 'usuario_id' já existe.")

    conn.close()

if __name__ == '__main__':
    adicionar_coluna_usuario_id()
