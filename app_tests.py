# app.py

from flask import Flask, render_template, request, redirect, url_for, flash
from gestor_serveis import (
    DB_PATH, crear_esquema_base, buscar_treballadors, 
    obtenir_treballador_per_id, obtenir_totes_les_rotacions,
    canviar_rotacio_treballador, canviar_dades_treballador, 
    eliminar_treballador
)
import os
from datetime import datetime

app = Flask(__name__)
# Cal una clau secreta per usar flash (missatges de sessió)
app.secret_key = 'clau_molt_secreta_i_llarga_per_serveis'

# Assegurar-se que la BD de prova existeix en iniciar l'app
if not os.path.exists(DB_PATH):
    crear_esquema_base(DB_PATH)

# ============================================================================
# RUTES PRINCIPALS
# ============================================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Ruta principal. Permet cercar treballadors (Funció 1) i mostra resultats.
    """
    resultats = []
    terme_cerca = ""
    
    if request.method == 'POST':
        terme_cerca = request.form.get('cerca', '').strip()
        if terme_cerca:
            resultats = buscar_treballadors(DB_PATH, terme_cerca)
            if not resultats:
                flash(f"❌ No s'ha trobat cap treballador amb '{terme_cerca}'.", 'danger')
        else:
            flash("🔍 Introdueix un terme de cerca (nom, ID o plaça).", 'warning')

    # Si es fa GET i no hi ha cerca, es mostra la llista de tots (simulant el comportament inicial)
    if request.method == 'GET' and not terme_cerca:
         resultats = buscar_treballadors(DB_PATH, '')

    return render_template('index.html', resultats=resultats, terme_cerca=terme_cerca)

@app.route('/treballador/<int:treballador_id>')
def veure_treballador(treballador_id):
    """
    Ruta per veure el detall d'un treballador (Funció 2) i els formularis de gestió (3, 4, 5).
    """
    treballador = obtenir_treballador_per_id(DB_PATH, treballador_id)
    rotacions_disponibles = obtenir_totes_les_rotacions(DB_PATH)
    
    if not treballador:
        flash("❌ Treballador no trobat.", 'danger')
        return redirect(url_for('index'))
        
    return render_template(
        'treballador.html', 
        t=treballador, # Utilitzem 't' per brevetat a la plantilla
        rotacions_disponibles=rotacions_disponibles
    )

# ============================================================================
# RUTES D'ACCIÓ (CRUD - Funcions 3, 4, 5)
# ============================================================================

@app.route('/rotacio/<int:treballador_id>', methods=['POST'])
def canviar_rotacio(treballador_id):
    """
    Canvi de rotació (Funció 3)
    """
    nova_rotacio = request.form.get('nova_rotacio').strip()
    
    if not nova_rotacio:
        flash("❌ Has de seleccionar una rotació vàlida.", 'danger')
    elif canviar_rotacio_treballador(DB_PATH, treballador_id, nova_rotacio):
        flash(f"✅ Rotació canviada a '{nova_rotacio}' correctament.", 'success')
    else:
        flash("❌ No s'ha pogut canviar la rotació. La rotació no existeix o no hi ha canvis.", 'danger')
        
    return redirect(url_for('veure_treballador', treballador_id=treballador_id))


@app.route('/modificar_dades/<int:treballador_id>', methods=['POST'])
def modificar_dades(treballador_id):
    """
    Canvi de plaça/zona/contracte_fi (Funció 4)
    """
    nova_plaza = request.form.get('nova_plaza').strip()
    nova_zona = request.form.get('nova_zona').strip()
    contracte_fi = request.form.get('contracte_fi').strip() # Pot ser buit
    
    if not nova_plaza or not nova_zona:
        flash("❌ La plaça i la zona són camps obligatoris.", 'danger')
    elif contracte_fi and not datetime_validator(contracte_fi):
        flash("❌ Format de data de fi de contracte incorrecte (YYYY-MM-DD).", 'danger')
    elif canviar_dades_treballador(DB_PATH, treballador_id, nova_plaza, nova_zona, contracte_fi):
        flash("✅ Dades de plaça, zona i/o contracte actualitzades correctament.", 'success')
    else:
        flash("❌ No s'ha pogut actualitzar les dades del treballador.", 'danger')
        
    return redirect(url_for('veure_treballador', treballador_id=treballador_id))

def datetime_validator(date_text):
    """ Funció auxiliar de validació de format de data """
    if not date_text: return True # Si és buit, és vàlid
    try:
        datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False

@app.route('/eliminar/<int:treballador_id>', methods=['POST'])
def eliminar_treballador_web(treballador_id):
    """
    Eliminar treballador (Funció 5)
    """
    if eliminar_treballador(DB_PATH, treballador_id)[0]:
        flash(f"✅ Treballador ID {treballador_id} eliminat correctament (i els seus descansos si existien).", 'success')
        return redirect(url_for('index')) # Redirigeix a la pàgina principal després d'eliminar
    else:
        flash(f"❌ No s'ha pogut eliminar el treballador ID {treballador_id}.", 'danger')
        return redirect(url_for('veure_treballador', treballador_id=treballador_id))


if __name__ == '__main__':
    app.run(debug=True)
