# app/routes/inmates.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import mysql
from .auth import login_required, admin_required
import MySQLdb.cursors
from datetime import date

inmates_bp = Blueprint('inmates', __name__)

# This is the main page for listing all inmates.
@inmates_bp.route('/inmates')
@login_required
def view_inmates():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Ensure photo_url is selected
    cur.execute("""
        SELECT i.*, c.cell_number 
        FROM inmates i
        LEFT JOIN cells c ON i.cell_id = c.id
        ORDER BY i.name
    """)
    inmates = cur.fetchall()
    cur.close()
    return render_template('inmates.html', inmates=inmates)

# Handles adding a new inmate from the modal form.
@inmates_bp.route('/add_inmate', methods=['POST'])
@admin_required
def add_inmate():
    name = request.form['name']
    crime = request.form['crime']
    sentence = request.form['sentence']
    sentence_duration = request.form['sentence_duration']
    admission_date = request.form['admission_date']
    release_date = request.form['release_date']
    photo_url = request.form.get('photo_url', '').strip() # Get the new photo_url field
    
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO inmates (name, crime, sentence, sentence_duration, admission_date, release_date, photo_url, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')
    """, (name, crime, sentence, sentence_duration, admission_date, release_date, photo_url))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Inmate added successfully"}), 201

# Handles editing an inmate's details from the modal form.
@inmates_bp.route('/edit_inmate/<int:id>', methods=['POST'])
@admin_required
def edit_inmate(id):
    name = request.form['name']
    crime = request.form['crime']
    sentence = request.form['sentence']
    sentence_duration = request.form['sentence_duration']
    release_date = request.form['release_date']
    photo_url = request.form.get('photo_url', '').strip() # Get the new photo_url field
    
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE inmates 
        SET name=%s, crime=%s, sentence=%s, sentence_duration=%s, release_date=%s, photo_url=%s
        WHERE id=%s
    """, (name, crime, sentence, sentence_duration, release_date, photo_url, id))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Inmate updated successfully"}), 200

# Handles deleting an inmate.
@inmates_bp.route('/delete_inmate/<int:id>', methods=['POST'])
@admin_required
def delete_inmate(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM inmates WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Inmate deleted successfully"}), 200


# ==============================================================================
# == INMATE PROFILE FEATURE ====================================================
# ==============================================================================
@inmates_bp.route('/inmate_profile/<int:id>')
@login_required
def inmate_profile(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT i.*, c.cell_number FROM inmates i LEFT JOIN cells c ON i.cell_id = c.id WHERE i.id = %s", (id,))
    inmate = cur.fetchone()

    if not inmate:
        flash('Inmate not found.', 'danger')
        return redirect(url_for('search.search'))

    cur.execute("SELECT * FROM punishments WHERE inmate_id = %s ORDER BY date_given DESC", (id,))
    punishments = cur.fetchall()

    cur.execute("SELECT * FROM transfers WHERE inmate_id = %s ORDER BY transfer_date DESC", (id,))
    transfers = cur.fetchall()

    cur.execute("SELECT * FROM work_assignments WHERE inmate_id = %s ORDER BY assigned_date DESC", (id,))
    work_assignments = cur.fetchall()

    cur.close()

    return render_template(
        'inmate_profile.html', 
        inmate=inmate, 
        punishments=punishments, 
        transfers=transfers,
        work_assignments=work_assignments
    )
