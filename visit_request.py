from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import mysql
from datetime import datetime, date
from .auth import login_required
import uuid
import MySQLdb.cursors

visit_request_bp = Blueprint('visit_request', __name__)

@visit_request_bp.route('/visit_request', methods=['GET', 'POST'])
def visit_request():
    if request.method == 'POST':
        visitor_name = request.form.get('visitor_name')
        inmate_name = request.form.get('inmate_name')
        relation = request.form.get('relation', '').strip()
        date_requested = request.form.get('date_requested')
        
        if not all([visitor_name, inmate_name, relation, date_requested]):
            flash("All fields are required.", "danger")
            return redirect(url_for('visit_request.visit_request'))

        tracking_id = uuid.uuid4().hex
        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO visit_requests (visitor_name, inmate_name, relation, date_requested, tracking_id) VALUES (%s, %s, %s, %s, %s)",
                (visitor_name, inmate_name, relation, date_requested, tracking_id)
            )
            notification_message = f"New visit request from '{visitor_name}' for inmate '{inmate_name}'."
            cur.execute("INSERT INTO notifications (message, target_audience) VALUES (%s, 'staff')", (notification_message,))
            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred: {e}", "danger")
            return redirect(url_for('visit_request.visit_request'))
        finally:
            cur.close()
        
        return redirect(url_for('visit_request.confirmation', tracking_id=tracking_id))
    
    inmate_search_name = request.args.get('inmate_search_name', '').strip()
    inmates_found = []
    if inmate_search_name:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        search_term = f"%{inmate_search_name}%"
        cur.execute("SELECT id, name, photo_url FROM inmates WHERE LOWER(name) LIKE LOWER(%s) AND status = 'Active'", (search_term,))
        inmates_found = cur.fetchall()
        cur.close()

    return render_template('visit_request_form.html', 
                           inmates_found=inmates_found, 
                           inmate_search_name=inmate_search_name)

@visit_request_bp.route('/visit_request/confirmation/<tracking_id>')
def confirmation(tracking_id):
    return render_template('visit_request_confirmation.html', tracking_id=tracking_id)

@visit_request_bp.route('/check_visit_status', methods=['GET', 'POST'])
def check_visit_status():
    if request.method == 'POST':
        tracking_id = request.form.get('tracking_id')
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM visit_requests WHERE tracking_id = %s", (tracking_id,))
        visit = cur.fetchone()
        cur.close()
        return render_template('check_visit_status.html', visit_request=visit, not_found=(not visit))
    return render_template('check_visit_status.html')

@visit_request_bp.route('/manage_visits')
@login_required
def manage_visits():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM visit_requests ORDER BY date_requested DESC")
    visits = cur.fetchall()
    cur.close()
    return render_template('manage_visits.html', visits=visits)

@visit_request_bp.route('/update_visit_status/<int:id>/<status>')
@login_required
def update_visit_status(id, status):
    if status not in ['Approved', 'Rejected']:
        flash('Invalid status!', 'danger')
        return redirect(url_for('visit_request.manage_visits'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE visit_requests SET status = %s WHERE id = %s", (status, id))
    mysql.connection.commit()
    cur.close()
    flash(f'Visit status updated to {status}!', 'success')
    return redirect(url_for('visit_request.manage_visits'))

@visit_request_bp.route('/visitor_check_in', methods=['GET', 'POST'])
def visitor_check_in():
    if request.method == 'GET':
        return render_template('visitor_check_in.html')

    # Handle all POST requests
    action = request.form.get('action')
    tracking_id = request.form.get('tracking_id')
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        if action == 'verify':
            # ** FIX: Corrected database query syntax **
            cur.execute("SELECT * FROM visit_requests WHERE tracking_id = %s", (tracking_id,))
            visit = cur.fetchone()
            
            error_message = None
            if not visit:
                error_message = "Verification Failed: Invalid Tracking ID."
            elif visit['status'] != 'Approved':
                error_message = f"Verification Failed: Visit status is '{visit['status']}', not 'Approved'."
            elif visit['date_requested'] != date.today():
                error_message = f"Verification Failed: Visit is scheduled for {visit['date_requested'].strftime('%Y-%m-%d')}, not today."
            
            if error_message:
                flash(error_message, "danger")
                return redirect(url_for('visit_request.visitor_check_in'))
            
            cur.execute("SELECT id FROM inmates WHERE name = %s", (visit['inmate_name'],))
            inmate = cur.fetchone()
            inmate_id = inmate['id'] if inmate else 'UNKNOWN'
            
            verification_result = {
                'visitor_name': visit['visitor_name'],
                'inmate_name': visit['inmate_name'],
                'inmate_id': inmate_id,
                'relation': visit['relation'],
                'date_requested': visit['date_requested']
            }
            return render_template('visitor_check_in.html', verification_result=verification_result, tracking_id=tracking_id)

        elif action == 'confirm':
            cur.execute("SELECT * FROM visit_requests WHERE tracking_id = %s AND status = 'Approved'", (tracking_id,))
            visit = cur.fetchone()
            if not visit:
                 raise Exception("Visit request could not be re-verified. Please try again.")

            cur.execute("SELECT id FROM inmates WHERE name = %s", (visit['inmate_name'],))
            inmate = cur.fetchone()
            if not inmate:
                raise Exception(f"Inmate '{visit['inmate_name']}' not found in database.")
            
            cur.execute(
                "INSERT INTO visitors (visitor_name, inmate_id, visit_date, relation) VALUES (%s, %s, %s, %s)",
                (visit['visitor_name'], inmate['id'], date.today(), visit['relation'])
            )
            
            cur.execute("UPDATE visit_requests SET status = 'Completed' WHERE id = %s", (visit['id'],))
            mysql.connection.commit()
            flash(f"Check-in Successful: Visitor '{visit['visitor_name']}' has been logged.", "success")
            return redirect(url_for('visit_request.visitor_check_in'))
        
        else:
            flash("Invalid action specified.", "danger")
            return redirect(url_for('visit_request.visitor_check_in'))

    except Exception as e:
        mysql.connection.rollback()
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('visit_request.visitor_check_in'))
    finally:
        cur.close()
