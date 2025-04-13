from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your own secret key

# Database connection setup
def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="skill"
    )
    return conn

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_name = request.form['admin_name']
        admin_pass = request.form['admin_pass']

        # Database check for admin login
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE admin_name=%s AND admin_pass=%s", (admin_name, admin_pass))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin:
            session['logged_in'] = True
            session['role'] = 'admin'
            session['admin_name'] = admin['admin_name']
            flash('Welcome, Admin!')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials. Please try again.')
            return redirect(url_for('admin_login'))

    return render_template('login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'logged_in' in session and session['role'] == 'admin':
        return render_template('index.html')
    else:
        flash('Please log in as an admin to access this page.')
        return redirect(url_for('admin_login'))

# Route to get recruiter details
@app.route('/admin/recruiters', methods=['GET'])
def get_recruiters():
    if 'logged_in' in session and session['role'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Fetch recruiters and the number of scholarships they have posted
            cursor.execute("""
                SELECT r.rec_id, r.rec_name, r.rec_email, r.rec_org, r.rec_position, 
                       COUNT(j.job_id) AS scholarships_posted
                FROM recruiter r
                LEFT JOIN jobs j ON r.rec_id = j.rec_id
                GROUP BY r.rec_id, r.rec_name, r.rec_email, r.rec_org, r.rec_position
            """)
            recruiters = cursor.fetchall()

            cursor.close()
            conn.close()
            return jsonify(recruiters)
        except Exception as e:
            print(f"Error fetching recruiters: {e}")
            return jsonify({"error": "Failed to fetch recruiters"}), 500
    else:
        return jsonify({"error": "Unauthorized access"}), 401

# Route to get applicant details
@app.route('/admin/applicants', methods=['GET'])
def get_applicants():
    if 'logged_in' in session and session['role'] == 'admin':
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Fetch applicant details along with the count of scholarships applied for
            cursor.execute("""
                SELECT a.app_id, a.app_name, a.app_email, a.app_phone, a.app_institution, a.app_cgpa,
                       COUNT(ap.applied_id) AS scholarship_count
                FROM applicant a
                LEFT JOIN applied ap ON a.app_id = ap.app_id
                GROUP BY a.app_id
            """)
            applicants = cursor.fetchall()

            # Fetch the total number of applicants
            cursor.execute("SELECT COUNT(*) AS total_applicants FROM applicant")
            total_applicants = cursor.fetchone()['total_applicants']

            cursor.close()
            conn.close()

            if not applicants:
                return jsonify({"message": "No applicants found", "total_applicants": total_applicants}), 200
            return jsonify({"applicants": applicants, "total_applicants": total_applicants}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Unauthorized access"}), 401




@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('admin_login'))

@app.route('/admin/messages', methods=['GET'])
def admin_messages():
    if 'logged_in' in session and session['role'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, mess_role, mess_type, mess FROM messages")
        messages = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(messages)
    else:
        flash('Please log in as an admin to access this page.')
        return redirect(url_for('admin_login'))

@app.route('/admin/recruiter-requests', methods=['GET'])
def recruiter_requests():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT req_id, rec_name, rec_email, rec_web FROM requests")
    requests = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(requests)

# Helper function to send emails
def send_email(to_email, subject, body):
    sender_email = 'cijogeorge2002@gmail.com'
    sender_password = 'tbnm wcjg qhbh rdwt'
    
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = to_email
    message['Subject'] = subject

    message.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        
        text = message.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()

        print(f"Email successfully sent to {to_email}")

    except smtplib.SMTPException as e:
        print(f"Failed to send email to {to_email}: {str(e)}")


@app.route('/admin/handle-recruiter-action', methods=['POST'])
def handle_recruiter_action():
    data = request.json
    req_id = data.get('req_id')
    action = data.get('action')

    print(f"Received action: {action} for recruiter ID: {req_id}")  # Debugging log

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Fetch results as dictionary

    try:
        # Fetch recruiter request details as a dictionary
        cursor.execute("SELECT rec_name, rec_email, rec_pass, rec_web FROM requests WHERE req_id = %s", (req_id,))
        request_details = cursor.fetchone()

        if not request_details:
            print(f"No recruiter request found with ID: {req_id}")  # Debugging log
            return jsonify({'success': False, 'message': f'Request not found for recruiter ID: {req_id}'}), 404

        if action == 'accept':
            # Insert recruiter data into the recruiter table
            cursor.execute("""
                INSERT INTO recruiter (rec_name, rec_email, rec_pass, rec_web) 
                VALUES (%s, %s, %s, %s)
            """, (request_details['rec_name'], request_details['rec_email'], request_details['rec_pass'], request_details['rec_web']))

            print(f"Recruiter {request_details['rec_name']} accepted.")  # Debugging log

            # Send acceptance email
            send_email(request_details['rec_email'], 
                       'Recruiter Request Accepted', 
                       'Your recruiter access has been granted!')

            message = 'Recruiter accepted and added to the system.'

        elif action == 'decline':
            # Send rejection email
            send_email(request_details['rec_email'], 
                       'Recruiter Request Declined', 
                       'Unfortunately, your recruiter access request has been declined.')

            print(f"Recruiter {request_details['rec_name']} declined.")  # Debugging log

            message = 'Recruiter request declined.'

        # Remove the request after the action
        cursor.execute("DELETE FROM requests WHERE req_id = %s", (req_id,))
        conn.commit()

        return jsonify({'success': True, 'message': message})

    except Exception as e:
        print(f"Error handling recruiter action: {e}")  # Debugging log
        return jsonify({'success': False, 'message': f'Error occurred during action: {str(e)}'}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/admin/reports', methods=['GET'])
def admin_reports():
    if 'logged_in' in session and session['role'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Fetch application statuses and counts
            cursor.execute("""
                SELECT app_status, COUNT(*) AS count
                FROM applied
                GROUP BY app_status
            """)
            report_data = cursor.fetchall()

            cursor.close()
            conn.close()
            return jsonify(report_data)
        except Exception as e:
            print(f"Error generating report: {e}")
            return jsonify({"error": "Failed to generate report"}), 500
    else:
        return jsonify({"error": "Unauthorized access"}), 401

@app.route('/admin/reports/<status>', methods=['GET'])
def report_details(status):
    if 'logged_in' in session and session['role'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Fetch applicants for the given status
            cursor.execute("""
    SELECT a.applied_id, a.job_id, a.app_id, a.app_status, 
           j.job_name, ap.app_name, ap.app_email, ap.app_course, ap.app_cgpa
    FROM applied a
    JOIN jobs j ON a.job_id = j.job_id
    JOIN applicant ap ON a.app_id = ap.app_id
    WHERE a.app_status = %s
""", (status,))

            applicants = cursor.fetchall()

            cursor.close()
            conn.close()
            return jsonify(applicants)
        except Exception as e:
            print(f"Error fetching details for status {status}: {e}")
            return jsonify({"error": "Failed to fetch details"}), 500
    else:
        return jsonify({"error": "Unauthorized access"}), 401


if __name__ == '__main__':
    app.run(debug=True)
