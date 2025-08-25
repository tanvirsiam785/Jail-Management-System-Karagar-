from app import mysql
import MySQLdb.cursors
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from .auth import login_required, admin_required

alerts_bp = Blueprint('alerts', __name__)

# MANUAL ALERTS CREATION
@alerts_bp.route('/alerts/create', methods=['POST'])
@admin_required
def create_alert():
    inmate_id = request.form.get('inmate_id')
    message = request.form.get('message')
    alert_date = request.form.get('alert_date') or datetime.now().strftime('%Y-%m-%d')

    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO alerts (inmate_id, alert_type, alert_date, message) VALUES (%s, %s, %s, %s)",
        (inmate_id, 'manual', alert_date, message)
    )
    mysql.connection.commit()
    cur.close()
    flash("Alert created successfully!", "success")
    return redirect(url_for('alerts.alerts_list'))

# DELETE ALERT
@alerts_bp.route('/alerts/delete/<int:id>', methods=['POST'])
def delete_alert(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM alerts WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Alert deleted successfully!", "danger")
    return redirect(url_for('alerts.alerts_list'))

# LIST ALERTS
@alerts_bp.route('/alerts')
@login_required
def alerts_list():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT a.id, a.message, a.alert_date, i.name AS inmate_name 
        FROM alerts a 
        LEFT JOIN inmates i ON a.inmate_id = i.id 
        ORDER BY a.alert_date ASC
    """)
    alerts = cur.fetchall()
    cur.close()
    return render_template("alerts.html", alerts=alerts)

# UPCOMING RELEASES (Next 7 Days)
@alerts_bp.route('/alerts/upcoming')
@login_required
def upcoming_releases():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = """
        SELECT id, name, release_date
        FROM inmates
        WHERE release_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
        ORDER BY release_date ASC
    """
    cur.execute(query)
    releases = cur.fetchall()
    cur.close()
    return render_template("upcoming_releases.html", releases=releases)

# API FOR BELL NOTIFICATIONS
@alerts_bp.route('/api/alerts')
@login_required
def api_alerts():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT a.id, a.message, a.alert_date, i.name AS inmate_name
        FROM alerts a 
        LEFT JOIN inmates i ON a.inmate_id = i.id
        ORDER BY a.alert_date ASC
        LIMIT 10
    """)
    alerts = cur.fetchall()
    cur.close()
    return jsonify(alerts)
from apscheduler.schedulers.background import BackgroundScheduler

def start_scheduler(app=None):

    scheduler = BackgroundScheduler()


    scheduler.add_job(func=generate_release_alerts, trigger="cron", hour=0, minute=0)

    scheduler.start()
    print("Alert scheduler started.")

def generate_release_alerts():
    """Generate release alerts for inmates releasing in the next 7 days."""
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = """
        SELECT id, name, release_date
        FROM inmates
        WHERE release_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
    """
    cur.execute(query)
    inmates = cur.fetchall()

    for inmate in inmates:
        # Check if alert already exists
        cur.execute("SELECT * FROM alerts WHERE inmate_id=%s AND alert_type='release'", (inmate['id'],))
        existing = cur.fetchone()
        if not existing:
            message = f"Inmate {inmate['name']} will be released on {inmate['release_date']}"
            cur.execute(
                "INSERT INTO alerts (inmate_id, alert_type, alert_date, message) VALUES (%s,%s,%s,%s)",
                (inmate['id'], 'release', datetime.now(), message)
            )
            mysql.connection.commit()

    cur.close()
    print("Release alerts generated.")
