# gestor_serveis.py

import sqlite3
import os
from datetime import datetime
from collections import defaultdict

# El path de la BD es manté
DB_PATH = 'treballadors.db'

# ============================================================================
# FUNCIONS AUXILIARS DE BD
# ============================================================================

def obtenir_connexio(db_path=DB_PATH):
    """Crea una connexió a la base de dades"""
    conn = sqlite3.connect(db_path)
    # Important per obtenir resultats com a diccionaris/objectes
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================================
# 1. CERCA I LLISTAT (Opció 1)
# ============================================================================

def buscar_treballadors(db_path, terme_cerca):
    """Busca treballadors per nom/treballador, id o plaça i retorna llistes de dicts"""
    conn = obtenir_connexio(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, treballador, plaza, rotacio, zona, contracte_fi
        FROM treballadors
        WHERE id LIKE ? OR treballador LIKE ? OR plaza LIKE ?
        ORDER BY treballador
    ''', (f'%{terme_cerca}%', f'%{terme_cerca}%', f'%{terme_cerca}%'))
    resultats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return resultats

# ============================================================================
# 2. DETALL DEL TREBALLADOR (Opció 2)
# ============================================================================

def obtenir_treballador_per_id(db_path, treballador_id):
    """Obté un treballador per ID i informació addicional"""
    conn = obtenir_connexio(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            t.id, t.treballador, t.plaza, t.rotacio, t.zona, t.contracte_fi,
            r.dies_treballats, r.dies_descans
        FROM treballadors t
        LEFT JOIN rotacions r ON t.rotacio = r.rotacio_nom
        WHERE t.id = ?
    ''', (treballador_id,))
    treballador = cursor.fetchone()
    conn.close()
    return dict(treballador) if treballador else None

def obtenir_totes_les_rotacions(db_path):
    """Retorna una llista de totes les rotacions disponibles"""
    conn = obtenir_connexio(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT rotacio_nom FROM rotacions ORDER BY rotacio_nom')
    rotacions = [row['rotacio_nom'] for row in cursor.fetchall()]
    conn.close()
    return rotacions

# ============================================================================
# 3. CANVI DE ROTACIÓ (Opció 3)
# ============================================================================

def canviar_rotacio_treballador(db_path, treballador_id, nova_rotacio):
    """Actualitza la rotació d'un treballador"""
    conn = obtenir_connexio(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE treballadors
            SET rotacio = ?
            WHERE id = ?
        ''', (nova_rotacio, treballador_id))
        conn.commit()
        return cursor.rowcount > 0 # Retorna True si s'ha modificat
    except Exception as e:
        print(f"Error canviant rotació: {e}")
        return False
    finally:
        conn.close()

# ============================================================================
# 4. CANVI DE PLAÇA/CONTRACTE (Opció 4)
# ============================================================================

def canviar_dades_treballador(db_path, treballador_id, nova_plaza, nova_zona, contracte_fi_str):
    """Actualitza la plaça, zona i/o data fi de contracte"""
    conn = obtenir_connexio(db_path)
    cursor = conn.cursor()
    
    # Gestionar data de fi de contracte
    if contracte_fi_str:
        try:
            # Validació (Flask ja farà validació de format a la vista)
            datetime.strptime(contracte_fi_str, '%Y-%m-%d')
            contracte_fi_db = contracte_fi_str
        except ValueError:
            return False # Error de format de data
    else:
        contracte_fi_db = None

    try:
        cursor.execute('''
            UPDATE treballadors
            SET plaza = ?, zona = ?, contracte_fi = ?
            WHERE id = ?
        ''', (nova_plaza, nova_zona, contracte_fi_db, treballador_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error canviant dades: {e}")
        return False
    finally:
        conn.close()

# ============================================================================
# 5. ELIMINAR TREBALLADOR (Opció 5)
# ============================================================================

def eliminar_treballador(db_path, treballador_id):
    """Elimina un treballador i els seus registres associats (descansos, etc.)"""
    conn = obtenir_connexio(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Eliminar descansos associats (Si la BD té la taula descansos_dies)
        # NOTA: Caldria verificar si la taula existeix. Assumim que existeix la taula 'descansos_dies'
        cursor.execute('DELETE FROM descansos_dies WHERE treballador_id = ?', (treballador_id,))
        descansos_eliminats = cursor.rowcount
        
        # 2. Eliminar el treballador
        cursor.execute('DELETE FROM treballadors WHERE id = ?', (treballador_id,))
        treballadors_eliminats = cursor.rowcount
        
        conn.commit()
        return treballadors_eliminats > 0, descansos_eliminats
        
    except sqlite3.OperationalError as e:
        # Pot passar si la taula 'descansos_dies' no existeix. Només eliminem el treballador
        if 'no such table' in str(e):
            print("⚠️ La taula 'descansos_dies' no existeix. S'elimina només de 'treballadors'.")
            cursor.execute('DELETE FROM treballadors WHERE id = ?', (treballador_id,))
            treballadors_eliminats = cursor.rowcount
            conn.commit()
            return treballadors_eliminats > 0, 0
        return False, 0
    except Exception as e:
        print(f"Error eliminant treballador: {e}")
        return False, 0
    finally:
        conn.close()

# ============================================================================
# FUNCIONS ADDICIONALS (Per omplir la BD de prova si no existeix)
# ============================================================================

def crear_esquema_base(db_path):
    """Crea un esquema mínim de la BD per a proves"""
    if os.path.exists(db_path):
        return # Ja existeix

    conn = obtenir_connexio(db_path)
    cursor = conn.cursor()
    
    # Taula treballadors
    cursor.execute('''
        CREATE TABLE treballadors (
            id INTEGER PRIMARY KEY,
            treballador TEXT NOT NULL,
            plaza TEXT,
            rotacio TEXT,
            zona TEXT,
            contracte_fi TEXT -- YYYY-MM-DD
        )
    ''')
    
    # Taula rotacions
    cursor.execute('''
        CREATE TABLE rotacions (
            rotacio_nom TEXT PRIMARY KEY,
            dies_treballats INTEGER,
            dies_descans INTEGER
        )
    ''')

    # Taula descansos_dies (necessària per Opció 5)
    cursor.execute('''
        CREATE TABLE descansos_dies (
            id INTEGER PRIMARY KEY,
            treballador_id INTEGER,
            data TEXT NOT NULL,
            origen TEXT,
            motiu TEXT,
            UNIQUE (treballador_id, data),
            FOREIGN KEY (treballador_id) REFERENCES treballadors(id)
        )
    ''')
    
    # Dades de prova (Treballadors)
    cursor.execute("INSERT INTO treballadors (id, treballador, plaza, rotacio, zona, contracte_fi) VALUES (1, 'Joan Garcia', 'Tècnic A', '4x2', 'Nord', '2026-12-31')")
    cursor.execute("INSERT INTO treballadors (id, treballador, plaza, rotacio, zona) VALUES (2, 'Maria López', 'Cap Equip', '5x2', 'Sud')")
    cursor.execute("INSERT INTO treballadors (id, treballador, plaza, rotacio, zona) VALUES (3, 'Pere Bosch', 'Tècnic B', '4x3', 'Nord')")
    
    # Dades de prova (Rotacions)
    cursor.execute("INSERT INTO rotacions (rotacio_nom, dies_treballats, dies_descans) VALUES ('4x2', 4, 2)")
    cursor.execute("INSERT INTO rotacions (rotacio_nom, dies_treballats, dies_descans) VALUES ('5x2', 5, 2)")
    cursor.execute("INSERT INTO rotacions (rotacio_nom, dies_treballats, dies_descans) VALUES ('4x3', 4, 3)")

    conn.commit()
    conn.close()
    print(f"✅ Base de dades de prova '{db_path}' creada amb dades mínimes.")