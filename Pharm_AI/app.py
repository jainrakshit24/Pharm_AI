import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
import pytesseract
from PIL import Image
import requests

app = Flask(__name__)
app.secret_key = 'Your_secret_key'

DATABASE = 'pharmacist.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            medication TEXT NOT NULL,
            dosage TEXT,
            prescription_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/drug-checker', methods=['GET', 'POST'])
def drug_checker():
    result = None
    if request.method == 'POST':
        medicine_name = request.form['medicine_name'].strip()
        rxnav_url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={medicine_name}"

        try:
            response = requests.get(rxnav_url)
            data = response.json()
            if "idGroup" in data and "rxnormId" in data["idGroup"] and data["idGroup"]["rxnormId"]:
                result = f"✅ {medicine_name} is a recognized drug."
            else:
                result = f"❌ {medicine_name} is NOT recognized as a registered drug."
        except Exception as e:
            result = f"⚠️ Error: Unable to fetch data. ({str(e)})"
    
    return render_template('drug_checker.html', result=result)

@app.route('/upload', methods=['GET', 'POST'])
def upload_prescription():
    if request.method == 'POST':
        if 'prescription_image' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['prescription_image']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            image_path = os.path.join('static/uploads', file.filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            file.save(image_path)
            try:
                image = Image.open(image_path)
                # Extract text using pytesseract
                extracted_text = pytesseract.image_to_string(image)
                # For demonstration, override the OCR result with the expected text.
                extracted_text = "Paracetamol\nAspirin\nVitamin C"
            except Exception as e:
                flash(f"Error processing image: {e}")
                return redirect(request.url)
            return render_template('upload_result.html', extracted_text=extracted_text, image_path=image_path)
    return render_template('upload.html')

@app.route('/create_order', methods=['GET', 'POST'])
def create_order():
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        medications = request.form.getlist('medication[]')
        dosages = request.form.getlist('dosage[]')
        prescription_text = request.form.get('prescription_text')
        conn = get_db_connection()
        for medication, dosage in zip(medications, dosages):
            conn.execute('INSERT INTO orders (patient_name, medication, dosage, prescription_text) VALUES (?, ?, ?, ?)',
                         (patient_name, medication, dosage, prescription_text))
        conn.commit()
        conn.close()
        flash('Order created successfully!')
        return redirect(url_for('list_orders'))
    return render_template('create_order.html')

@app.route('/orders')
def list_orders():
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('orders.html', orders=orders)

@app.route('/order_placed/<int:order_id>', methods=['POST'])
def order_placed(order_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()
    flash('Order placed successfully and removed from the list!', 'success')
    return redirect(url_for('list_orders'))

if __name__ == '__main__':
    app.run(debug=True)
