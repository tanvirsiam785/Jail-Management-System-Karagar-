# app/routes/transfers.py

from flask import Blueprint, render_template, request, jsonify
from app import mysql
from .auth import login_required, admin_required
import MySQLdb.cursors
from datetime import datetime

transfers_bp = Blueprint('transfers', __name__)

# ==============================================================================
# == VIEW ALL TRANSFERS ========================================================
# ==============================================================================
@transfers_bp.route('/transfers')
@login_required
def view_transfers():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT t.id, i.name AS inmate_name, t.from_cell, t.to_cell, 
               t.transfer_date, t.reason
        FROM transfers t
        JOIN inmates i ON t.inmate_id = i.id
        ORDER BY t.transfer_date DESC
    """)
    transfers = cur.fetchall()
    cur.close()
    return render_template('transfers.html', transfers=transfers)


# ==============================================================================
# == ADD NEW TRANSFER ==========================================================
# ==============================================================================
@transfers_bp.route('/add_transfer', methods=['POST'])
@admin_required
def add_transfer():
    inmate_id = request.form['inmate_id']
    from_cell = request.form['from_cell']
    to_cell = request.form['to_cell']
    reason = request.form.get('reason', '').strip()
    transfer_date = datetime.now().strftime("%Y-%m-%d")

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO transfers (inmate_id, from_cell, to_cell, transfer_date, reason)
        VALUES (%s, %s, %s, %s, %s)
    """, (inmate_id, from_cell, to_cell, transfer_date, reason))

    # Update inmate's current cell in inmates table
    cur.execute("UPDATE inmates SET cell_id = %s WHERE id = %s", (to_cell, inmate_id))

    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Transfer recorded successfully"}), 201


# ==============================================================================
# == DELETE TRANSFER ===========================================================
# ==============================================================================
@transfers_bp.route('/delete_transfer/<int:id>', methods=['POST'])
@admin_required
def delete_transfer(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM transfers WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Transfer deleted successfully"}), 200


# ==============================================================================
# == VIEW TRANSFERS FOR A SINGLE INMATE ========================================
# ==============================================================================
@transfers_bp.route('/inmate/<int:inmate_id>/transfers')
@login_required
def inmate_transfers(inmate_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT t.id, t.from_cell, t.to_cell, t.transfer_date, t.reason
        FROM transfers t
        WHERE t.inmate_id = %s
        ORDER BY t.transfer_date DESC
    """, (inmate_id,))
    transfers = cur.fetchall()
    cur.close()
    return render_template('inmate_transfers.html', transfers=transfers, inmate_id=inmate_id)
