from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import mysql.connector
from flask import send_from_directory, abort
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import smtplib
from email.mime.text import MIMEText
import os

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'learnaid'
app.config['UPLOAD_FOLDER'] = 'static/resumes'
ALLOWED_EXTENSIONS = {'pdf'}

def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="skill"
    )
    return conn


# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        app_name = request.form['app_name']
        app_pass = request.form['app_pass']

        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

       
        cursor.execute('SELECT * FROM applicant WHERE app_name=%s AND app_pass=%s', (app_name, app_pass))
        user = cursor.fetchone()

        if user:
            session['role'] = 'applicant'
            session['app_name'] = user['app_name']
            session['app_id'] = user['app_id']
            session['logged_in'] = True
            cursor.close()
            conn.close()
            return redirect(url_for('applicant_dashboard'))

        
        cursor.execute('SELECT * FROM recruiter WHERE rec_name=%s AND rec_pass=%s', (app_name, app_pass))
        user = cursor.fetchone()

        if user:
            session['role'] = 'recruiter'
            session['rec_name'] = user['rec_name']
            session['rec_id'] = user['rec_id']
            session['logged_in'] = True
            cursor.close()
            conn.close()
            return redirect(url_for('recruiter_dashboard'))

        flash('Invalid credentials. Please try again.')
        cursor.close()
        conn.close()
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        app_name = request.form['app_name']
        app_pass = request.form['app_pass']
        user_role = request.form['user_role']  # Get the role from the form

        conn = get_db_connection()
        cursor = conn.cursor()

        if user_role == 'applicant':
            cursor.execute("""
                INSERT INTO applicant (app_name, app_pass)
                VALUES (%s, %s)
            """, (app_name, app_pass))
            flash('Applicant signed up successfully!')
        elif user_role == 'recruiter':
            rec_web = request.form.get('rec_web')
            rec_email = request.form.get('rec_email')  # Get recruiter website
            cursor.execute("""
                INSERT INTO requests (rec_name, rec_pass, rec_email, rec_web)
                VALUES (%s, %s, %s, %s)
            """, (app_name, app_pass, rec_email, rec_web))
            flash('Recruiter sign up request sent successfully!')

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html')

# Home/index route
@app.route('/')
def index():
    if 'logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch jobs from the database
        cursor.execute('SELECT job_id, job_name, job_type, job_amount FROM jobs')
        jobs = cursor.fetchall()

        cursor.close()
        conn.close()

        # Route based on role
        if session['role'] == 'applicant':
            return render_template('applicant/index.html', jobs=jobs)
        elif session['role'] == 'recruiter':
            return render_template('recruiter/index.html', jobs=jobs)
        elif session['role'] == 'admin':
            return render_template('admin/index.html', jobs=jobs)
    else:
        return redirect(url_for('login'))

@app.route('/applicant_dashboard')
def applicant_dashboard():
    if 'logged_in' in session and session['role'] == 'applicant':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT job_id, job_name, job_type, job_amount FROM jobs')
        jobs = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('applicant/index.html', jobs=jobs)
    else:
        return redirect(url_for('login'))

@app.route('/recruiter_dashboard')
def recruiter_dashboard():
    if 'logged_in' in session and session['role'] == 'recruiter':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT job_id, job_name, job_type, job_amount FROM jobs')
        jobs = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('recruiter/index.html', jobs=jobs)
    else:
        return redirect(url_for('login'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'logged_in' in session and session['role'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT job_id, job_name, job_type, job_salary FROM jobs')
        jobs = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin/index.html', jobs=jobs)
    else:
        return redirect(url_for('login'))

# Logout route
@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for('login'))

# Job Detail route
@app.route('/job/<int:job_id>', methods=['GET'])
def job_detail(job_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch job details from the database
    cursor.execute("""
        SELECT job_id, job_name, job_type, job_amount, job_audience, job_desc, job_eligiblity, job_date, job_ddate, job_vac
        FROM jobs
        WHERE job_id = %s
    """, (job_id,))
    job = cursor.fetchone()

    cursor.close()
    conn.close()

    if job:
        # Split job_eligibility into a list for display
        job['job_eligiblity_list'] = job['job_eligiblity'].split(',')

        return render_template('applicant/job-detail.html', job=job)
    else:
        flash('Job not found!')
        return redirect(url_for('index'))



# Apply Job route
@app.route('/apply/<int:job_id>', methods=['POST'])
def apply_job(job_id):
    if 'logged_in' not in session or not session.get('app_id'):
        flash('Please log in to apply for the job.')
        return redirect(url_for('login'))

    app_id = session.get('app_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if the applicant's profile is complete
    cursor.execute("""
        SELECT app_cgpa, app_cv, app_email, app_course, app_institution
        FROM applicant
        WHERE app_id = %s
    """, (app_id,))
    profile = cursor.fetchone()

    # Validate the profile completeness
    if not profile or any(not profile[field] for field in ['app_cgpa', 'app_cv', 'app_email', 'app_course', 'app_institution']):
        flash('Please complete your profile (CGPA, Resume, Email, Course, and Institution) before applying for scholarships.')
        cursor.close()
        conn.close()
        return redirect(url_for('about'))  # Redirect to the profile page

    # Validate file upload
    if 'coverletter' not in request.files:
        flash('No cover letter uploaded.')
        cursor.close()
        conn.close()
        return redirect(request.url)

    coverletter_file = request.files['coverletter']
    if coverletter_file and allowed_file(coverletter_file.filename):
        filename = secure_filename(coverletter_file.filename)

        # Ensure the file is a PDF
        if not filename.lower().endswith('.pdf'):
            flash('Invalid file format. Only PDF files are allowed.')
            cursor.close()
            conn.close()
            return redirect(request.url)

        # Check if the applicant has already applied for the scholarship
        cursor.execute("""
            SELECT COUNT(*) AS count FROM applied WHERE job_id = %s AND app_id = %s
        """, (job_id, app_id))
        result = cursor.fetchone()

        if result['count'] > 0:
            flash('You have already applied for this scholarship.')
            cursor.close()
            conn.close()
            return redirect(url_for('job_detail', job_id=job_id))

        # Save the cover letter file
        coverletter_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Insert job_id, app_id, and app_cover into the applied table
        cursor.execute("""
            INSERT INTO applied (job_id, app_id, app_cover)
            VALUES (%s, %s, %s)
        """, (job_id, app_id, filename))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Application submitted successfully!')
        return redirect(url_for('job_detail', job_id=job_id))
    else:
        flash('Invalid file format. Only PDF files are allowed.')
        cursor.close()
        conn.close()
        return redirect(request.url)


@app.route('/about', methods=['GET', 'POST'])
def about():
    if 'logged_in' in session:
        role = session['role']

        # For Applicant
        if role == 'applicant':
            app_id = session['app_id']

            # Fetch applicant details
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM applicant WHERE app_id = %s", (app_id,))
            applicant = cursor.fetchone()
            cursor.close()
            conn.close()

            if request.method == 'POST':
                # Process form data and update applicant profile
                app_name = request.form['app_name']
                app_email = request.form['app_email']
                app_phone = request.form['app_phone']
                app_gender = request.form['app_gender']
                app_institution = request.form['app_institution']
                app_course = request.form['app_course']
                app_yearofstudy = request.form['app_yearofstudy']
                app_cgpa = request.form['app_cgpa']

                # File uploads for CV and cover letter
                app_cv = applicant['app_cv']
                app_letter = applicant['app_letter']

                if 'app_cv' in request.files and request.files['app_cv'].filename:
                    cv_file = request.files['app_cv']
                    app_cv = secure_filename(cv_file.filename)
                    cv_file.save(os.path.join(app.config['UPLOAD_FOLDER'], app_cv))

                if 'app_letter' in request.files and request.files['app_letter'].filename:
                    letter_file = request.files['app_letter']
                    app_letter = secure_filename(letter_file.filename)
                    letter_file.save(os.path.join(app.config['UPLOAD_FOLDER'], app_letter))

                # Update applicant in the database
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE applicant SET app_name = %s, app_email = %s, app_phone = %s, app_gender = %s, app_institution = %s,
                    app_course = %s, app_yearofstudy = %s, app_cgpa = %s, app_cv = %s, app_letter = %s
                    WHERE app_id = %s
                """, (app_name, app_email, app_phone, app_gender, app_institution, app_course, app_yearofstudy, app_cgpa, app_cv, app_letter, app_id))
                conn.commit()
                cursor.close()
                conn.close()

                flash('Applicant profile updated successfully!')
                return redirect(url_for('about'))

            return render_template('applicant/about.html', applicant=applicant)

        # For Recruiter
        elif role == 'recruiter':
            rec_id = session['rec_id']

            # Fetch recruiter details
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM recruiter WHERE rec_id = %s", (rec_id,))
            recruiter = cursor.fetchone()
            cursor.close()
            conn.close()

            if request.method == 'POST':
                # Process form data and update recruiter profile
                rec_name = request.form['rec_name']
                rec_email = request.form['rec_email']
                rec_phone = request.form['rec_phone']
                rec_org = request.form['rec_org']
                rec_position = request.form['rec_position']
                rec_web = request.form['rec_web']

                # Update recruiter in the database
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE recruiter SET rec_name = %s, rec_email = %s, rec_phone = %s, rec_org = %s, rec_position = %s, rec_web = %s
                    WHERE rec_id = %s
                """, (rec_name, rec_email, rec_phone, rec_org, rec_position, rec_web, rec_id))
                conn.commit()
                cursor.close()
                conn.close()

                flash('Recruiter profile updated successfully!')
                return redirect(url_for('about'))

            return render_template('recruiter/about.html', recruiter=recruiter)

    else:
        flash('Please log in to access this page.')
        return redirect(url_for('login'))


@app.route('/view_cv/<filename>')
def view_cv(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        abort(404)

@app.route('/view_cover_letter/<filename>')
def view_cover_letter(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        abort(404)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Get the form data
        mess_type = request.form['messageType']
        mess = request.form['message']

        # Check if user is logged in and determine their role
        if 'logged_in' in session:
            if 'app_id' in session:
                mess_role = 'applicant'
                user_id = session['app_id']
                user_name = session.get('app_name', 'Anonymous')  # Adjust key for applicant's name
            elif 'rec_id' in session:
                mess_role = 'recruiter'
                user_id = session['rec_id']
                user_name = session.get('rec_name', 'Anonymous')  # Adjust key for recruiter's name
            else:
                # If neither app_id nor rec_id is in the session
                flash("Error: Unable to determine user role.", "danger")
                return redirect(url_for('contact'))

            # Insert the message into the messages table
            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO messages (name, mess_role, mess, mess_type) 
                    VALUES (%s, %s, %s, %s)
                """, (user_name, mess_role, mess, mess_type))
                conn.commit()
                flash('Your message has been sent successfully!', 'success')
            except Exception as e:
                print(f"Error inserting message: {e}")
                flash('An error occurred while sending your message. Please try again.', 'danger')
            finally:
                cursor.close()
                conn.close()
        else:
            flash('You must be logged in to send a message.', 'warning')

        return redirect(url_for('contact'))

    # Render the contact form
    return render_template('contact.html')


#recruiter
@app.route('/recruiter/job/<int:job_id>', methods=['GET'])
def recruiter_job_detail(job_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch job details from the database
    cursor.execute("""
        SELECT job_id, job_name, job_type, job_amount, job_audience, job_desc, job_eligiblity, job_date, job_ddate, job_vac
        FROM jobs
        WHERE job_id = %s
    """, (job_id,))
    job = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if job:
            # Split job_eligibility into a list for display
            job['job_eligiblity_list'] = job['job_eligiblity'].split(',')

            return render_template('recruiter/job-detail.html', job=job)
    else:
            flash('Job not found!')
            return redirect(url_for('index'))

# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    if os.path.exists(file_path):
        reader = PdfReader(file_path)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
        return text
    else:
        return ''  # Return an empty string if the file doesn't exist

# Function to calculate similarity score between two texts
def calculate_similarity(text1, text2):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text1, text2])
    similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    return similarity_score[0][0]

@app.route('/applied')
def applied():
    if 'logged_in' in session and session['role'] == 'recruiter':
        rec_id = session.get('rec_id')

        # Fetch applicants who have applied to jobs posted by the logged-in recruiter
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.app_id, a.app_name, a.app_email, a.app_cv, a.app_letter, app.app_cover, app.job_id, 
                j.job_name, j.job_eligiblity, j.job_audience, j.job_income
            FROM applied app
            JOIN applicant a ON app.app_id = a.app_id
            JOIN jobs j ON app.job_id = j.job_id
            WHERE j.rec_id = %s
        """, (rec_id,))

        applicants = cursor.fetchall()
        cursor.close()
        conn.close()

        scored_applicants = []
        for applicant in applicants:
            # Get job eligibility, audience, and income from the current applicant's job
            job_eligibility = applicant['job_eligiblity']
            job_audience = applicant['job_audience']
            job_income = applicant['job_income']

            # Construct file paths for CV and cover letter
            cv_file_path = os.path.join(app.config['UPLOAD_FOLDER'], applicant['app_cv'])
            letter_file_path = os.path.join(app.config['UPLOAD_FOLDER'], applicant['app_letter']) if applicant['app_letter'] else None

            # Extract text from CV
            cv_text = extract_text_from_pdf(cv_file_path)

            # Calculate similarity score with job eligibility and audience
            eligibility_score = calculate_similarity(cv_text, job_eligibility)
            audience_score = calculate_similarity(cv_text, job_audience)

            # If job_income is defined, process cover letter (if available)
            if job_income and letter_file_path and os.path.exists(letter_file_path):
                cover_letter_text = extract_text_from_pdf(letter_file_path)
                income_score = calculate_similarity(cover_letter_text, job_income)
            else:
                income_score = 1.0  # Default max score if no income requirement or letter

            # Calculate a combined score
            total_score = (eligibility_score * 0.5) + (audience_score * 0.3) + (income_score * 0.2)

            applicant['total_score'] = total_score
            scored_applicants.append(applicant)

        # Sort applicants based on total score
        sorted_applicants = sorted(scored_applicants, key=lambda x: x['total_score'], reverse=True)

        return render_template('recruiter/applied.html', applicants=sorted_applicants)

    flash('Please log in as a recruiter to view the applicants.')
    return redirect(url_for('login'))

@app.route('/applicant/<int:app_id>/<int:job_id>')
def applicant_details(app_id, job_id):
    if 'logged_in' in session and session['role'] == 'recruiter':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Fetch applicant details and application status for the specific job_id
            cursor.execute("""
                SELECT a.app_id, a.app_name, a.app_email, a.app_phone, a.app_gender,
                       a.app_institution, a.app_course, a.app_yearofstudy, a.app_cgpa,
                       a.app_cv, a.app_letter, ap.app_status
                FROM applicant a
                JOIN applied ap ON a.app_id = ap.app_id
                WHERE a.app_id = %s AND ap.job_id = %s
            """, (app_id, job_id))
            applicant = cursor.fetchone()

            if applicant:
                return render_template('recruiter/appdets.html', applicant=applicant)
            else:
                flash('Applicant not found for the selected scholarship.')
                return redirect(url_for('applied'))
        except Exception as e:
            print(f"Error fetching applicant details: {e}")
            flash('An error occurred while fetching applicant details.')
            return redirect(url_for('applied'))
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Please log in to access this page.')
        return redirect(url_for('login'))

@app.route('/post', methods=['GET', 'POST'])
def post_scholarship():
    if 'logged_in' in session and session['role'] == 'recruiter':
        rec_id = session['rec_id']  # Get the recruiter ID from the session

        if request.method == 'POST':
            # Get the form data
            job_name = request.form['job_name']
            job_type = request.form['job_type']
            job_amount = request.form['job_amount']
            job_audience = request.form['job_audience']
            job_desc = request.form['job_desc']
            job_eligiblity = request.form['job_eligiblity']
            job_date = request.form['job_date']
            job_ddate = request.form['job_ddate']
            job_vac = request.form['job_vac']
            job_nature = request.form['job_nature']

            # Insert the new scholarship into the jobs table
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (rec_id, job_name, job_type, job_amount, job_audience, job_desc, job_eligiblity, job_date, job_ddate, job_vac, job_nature)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (rec_id, job_name, job_type, job_amount, job_audience, job_desc, job_eligiblity, job_date, job_ddate, job_vac, job_nature))
            conn.commit()
            cursor.close()
            conn.close()

            flash('Scholarship posted successfully!')
            return redirect(url_for('recruiter_dashboard'))  # Redirect to the recruiter dashboard after posting

        return render_template('recruiter/post.html')  # Display the post form for recruiters

    else:
        flash('You must be logged in as a recruiter to post a scholarship.')
        return redirect(url_for('login'))

@app.route('/scholarships')
def scholarships():
    if 'logged_in' in session and session['role'] == 'recruiter':
        rec_id = session['rec_id']
        
        # Fetch scholarships posted by the logged-in recruiter
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT job_id, job_name, job_type, job_amount, job_audience, job_date, job_ddate, job_vac, job_nature
            FROM jobs
            WHERE rec_id = %s
        """, (rec_id,))
        scholarships = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template('recruiter/scholarships.html', scholarships=scholarships)

    flash('Please log in as a recruiter to view your scholarships.')
    return redirect(url_for('login'))

@app.route('/update_scholarship/<int:job_id>', methods=['GET', 'POST'])
def update_scholarship(job_id):
    if request.method == 'POST':
        # Fetch the updated details from the form
        job_name = request.form['job_name']
        job_type = request.form['job_type']
        job_amount = request.form['job_amount']
        job_audience = request.form['job_audience']
        job_desc = request.form['job_desc']
        job_eligiblity = request.form['job_eligiblity']
        job_ddate = request.form['job_ddate']
        job_vac = request.form['job_vac']
        job_nature = request.form['job_nature']

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update the scholarship details in the database
        cursor.execute("""
            UPDATE jobs 
            SET job_name = %s, job_type = %s, job_amount = %s, job_audience = %s, job_desc = %s, 
                job_eligiblity = %s, job_ddate = %s, job_vac = %s, job_nature = %s
            WHERE job_id = %s AND rec_id = %s
        """, (job_name, job_type, job_amount, job_audience, job_desc, job_eligiblity, job_ddate, job_vac, job_nature, job_id, session['rec_id']))
        
        conn.commit()
        cursor.close()
        conn.close()

        flash('Scholarship updated successfully!')
        return redirect(url_for('scholarships'))

    # Handle GET request to display the form for updating scholarship details
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jobs WHERE job_id = %s AND rec_id = %s", (job_id, session['rec_id']))
    scholarship = cursor.fetchone()
    cursor.close()
    conn.close()

    if scholarship:
        return render_template('recruiter/update_scholarship.html', scholarship=scholarship)
    else:
        flash('Scholarship not found.')
        return redirect(url_for('scholarships'))


@app.route('/delete_scholarship/<int:job_id>', methods=['POST'])
def delete_scholarship(job_id):
    if 'logged_in' in session and session['role'] == 'recruiter':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Only allow the recruiter who posted the job to delete it
        cursor.execute('DELETE FROM jobs WHERE job_id = %s AND rec_id = %s', (job_id, session['rec_id']))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Scholarship deleted successfully!')
        return redirect(url_for('scholarships'))

    flash('Please log in as a recruiter to delete the scholarship.')
    return redirect(url_for('login'))

@app.route('/process_application/<int:app_id>', methods=['POST'])
def process_application(app_id):
    if 'logged_in' not in session or session.get('role') != 'recruiter':
        flash('Unauthorized access. Please log in as a recruiter.')
        return redirect(url_for('login'))

    action = request.form.get('action')  # Accept or Decline
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch applicant email using a JOIN
        cursor.execute("""
            SELECT a.app_email 
            FROM applied ap
            JOIN applicant a ON ap.app_id = a.app_id
            WHERE ap.app_id = %s
        """, (app_id,))
        applicant = cursor.fetchone()

        # Ensure the result is fully consumed to avoid unread results
        cursor.fetchall()  # Clear any remaining results

        if not applicant:
            flash('Applicant not found!')
            return redirect(url_for('index'))

        applicant_email = applicant['app_email']

        # Update application status based on the action
        if action == 'accept':
            cursor.execute("""
                UPDATE applied
                SET app_status = 'Accepted'
                WHERE app_id = %s
            """, (app_id,))
            conn.commit()

            # Send notification
            send_email_notification(applicant_email, 'Accepted')
            flash(f'Application {app_id} has been accepted!')

        elif action == 'decline':
            cursor.execute("""
                UPDATE applied
                SET app_status = 'Declined'
                WHERE app_id = %s
            """, (app_id,))
            conn.commit()

            # Send notification
            send_email_notification(applicant_email, 'Declined')
            flash(f'Application {app_id} has been declined!')

        else:
            flash('Invalid action.')
            return redirect(url_for('index'))

    except Exception as e:
        print(f"Error processing application: {e}")
        flash('An error occurred while processing the application.')
        return redirect(url_for('index'))

    finally:
        # Always close the cursor and connection
        cursor.close()
        conn.close()

    return redirect(url_for('applied'))  # Redirect to the applications page


def send_email_notification(email, status):
    subject = f"Your Application Status: {status}"
    body = f"Dear Applicant,\n\nYour application has been {status}. Thank you for applying.\n\nBest Regards,\nLearnAid Team"
    
    sender_email = "your_email@example.com"
    sender_password = "your_password"

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
            print(f"Email sent to {email} for status {status}")
    except Exception as e:
        print(f"Failed to send email to {email}: {e}")


@app.route('/applied_for')
def applied_for():
    if 'logged_in' in session and session['role'] == 'applicant':
        app_id = session['app_id']  # Get the app_id from the session
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch applied scholarships for the logged-in student
        cursor.execute("""
            SELECT a.applied_id, a.job_id, a.app_cover, a.app_status, j.job_name, j.job_amount, j.job_desc
            FROM applied a
            JOIN jobs j ON a.job_id = j.job_id
            WHERE a.app_id = %s
        """, (app_id,))
        applied_scholarships = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('applicant/applied_for.html', applied_scholarships=applied_scholarships)
    else:
        flash("Please log in to view your applied scholarships.")
        return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
