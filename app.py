from flask import Flask, render_template, request, redirect, url_for, flash, Response
import csv
from io import StringIO
from database import init_db, get_db_connection

app = Flask(__name__)
app.secret_key = 'vguard_secret_key_change_in_prod'

# Initialize database on startup
init_db()

@app.route('/')
def dashboard():
    conn = get_db_connection()
    
    # Get stats
    total_issued = conn.execute("SELECT COUNT(*) FROM transactions WHERE status = 'Issued'").fetchone()[0]
    total_used = conn.execute("SELECT COUNT(*) FROM transactions WHERE status = 'Used'").fetchone()[0]
    total_returned = conn.execute("SELECT COUNT(*) FROM transactions WHERE status = 'Returned'").fetchone()[0]
    
    # Get recent transactions
    recent_txs = conn.execute('''
        SELECT t.id, t.sr_number, tech.name as technician_name, comp.name as component_name, t.quantity, t.status, t.updated_at
        FROM transactions t
        JOIN technicians tech ON t.technician_id = tech.id
        JOIN components comp ON t.component_id = comp.id
        ORDER BY t.updated_at DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    return render_template('index.html', 
                         total_issued=total_issued, 
                         total_used=total_used, 
                         total_returned=total_returned,
                         recent_txs=recent_txs)

@app.route('/issue', methods=['GET', 'POST'])
def issue_component():
    conn = get_db_connection()
    if request.method == 'POST':
        sr_number = request.form['sr_number']
        technician_id = request.form['technician_id']
        component_ids = request.form.getlist('component_id[]')
        quantities = request.form.getlist('quantity[]')
        
        if not component_ids:
            flash('Please select at least one component.', 'error')
            return redirect(url_for('issue_component'))
            
        # Validate stock first
        for i in range(len(component_ids)):
            comp_id = component_ids[i]
            qty = int(quantities[i])
            stock = conn.execute('SELECT stock_quantity FROM components WHERE id = ?', (comp_id,)).fetchone()[0]
            if stock < qty:
                comp_name = conn.execute('SELECT name FROM components WHERE id = ?', (comp_id,)).fetchone()[0]
                flash(f'Not enough stock for {comp_name}! Requested {qty} but only {stock} left.', 'error')
                return redirect(url_for('issue_component'))
        
        # Insert all transactions
        for i in range(len(component_ids)):
            comp_id = component_ids[i]
            qty = int(quantities[i])
            
            conn.execute('''
                INSERT INTO transactions (sr_number, technician_id, component_id, quantity, status)
                VALUES (?, ?, ?, ?, 'Issued')
            ''', (sr_number, technician_id, comp_id, qty))
            
            # Decrease stock
            conn.execute('''
                UPDATE components SET stock_quantity = stock_quantity - ? WHERE id = ?
            ''', (qty, comp_id))
            
        conn.commit()
        conn.close()
        flash('Components issued successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    technicians = conn.execute('SELECT * FROM technicians').fetchall()
    components = conn.execute('SELECT * FROM components WHERE stock_quantity > 0').fetchall()
    conn.close()
    return render_template('issue.html', technicians=technicians, components=components)

@app.route('/update_status/<int:transaction_id>', methods=['POST'])
def update_status(transaction_id):
    new_status = request.form['status'] # 'Used' or 'Returned'
    conn = get_db_connection()
    
    # Check current status
    tx = conn.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
    if tx and tx['status'] == 'Issued':
        conn.execute('''
            UPDATE transactions 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (new_status, transaction_id))
        
        # If returned, put back in stock
        if new_status == 'Returned':
            conn.execute('''
                UPDATE components SET stock_quantity = stock_quantity + ? WHERE id = ?
            ''', (tx['quantity'], tx['component_id']))
        
        conn.commit()
        flash('Transaction updated successfully!', 'success')
    else:
        flash('Invalid transaction or already updated.', 'error')
        
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/search', methods=['GET'])
def search_history():
    query = request.args.get('sr_number', '').strip()
    history = []
    
    if query:
        conn = get_db_connection()
        history = conn.execute('''
            SELECT t.id, t.sr_number, tech.name as technician_name, comp.name as component_name, 
                   t.quantity, t.status, t.issued_at, t.updated_at
            FROM transactions t
            JOIN technicians tech ON t.technician_id = tech.id
            JOIN components comp ON t.component_id = comp.id
            WHERE t.sr_number = ?
            ORDER BY t.issued_at DESC
        ''', (query,)).fetchall()
        conn.close()
        
    return render_template('search.html', query=query, history=history)

@app.route('/staff', methods=['GET', 'POST'])
def manage_staff():
    conn = get_db_connection()
    if request.method == 'POST':
        new_name = request.form['name'].strip()
        if new_name:
            conn.execute('INSERT INTO technicians (name) VALUES (?)', (new_name,))
            conn.commit()
            flash('Technician added successfully!', 'success')
        else:
            flash('Name cannot be empty.', 'error')
        return redirect(url_for('manage_staff'))
        
    technicians = conn.execute('SELECT * FROM technicians ORDER BY name').fetchall()
    conn.close()
    return render_template('staff.html', technicians=technicians)

@app.route('/delete_staff/<int:id>', methods=['POST'])
def delete_staff(id):
    conn = get_db_connection()
    # Safety Check: Does this staff have transactions?
    count = conn.execute('SELECT COUNT(*) FROM transactions WHERE technician_id = ?', (id,)).fetchone()[0]
    if count > 0:
        flash('Cannot delete technician because they have existing transaction records!', 'error')
    else:
        conn.execute('DELETE FROM technicians WHERE id = ?', (id,))
        conn.commit()
        flash('Technician deleted safely.', 'success')
        
    conn.close()
    return redirect(url_for('manage_staff'))

@app.route('/components', methods=['GET', 'POST'])
def manage_components():
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name'].strip()
        stock = request.form['stock']
        if name and stock.isdigit():
            conn.execute('INSERT INTO components (name, stock_quantity) VALUES (?, ?)', (name, int(stock)))
            conn.commit()
            flash('Component added successfully!', 'success')
        else:
            flash('Invalid input. Name and valid stock amount required.', 'error')
        return redirect(url_for('manage_components'))
        
    components = conn.execute('SELECT * FROM components ORDER BY name').fetchall()
    conn.close()
    return render_template('components.html', components=components)

@app.route('/delete_component/<int:id>', methods=['POST'])
def delete_component(id):
    conn = get_db_connection()
    # Safety Check
    count = conn.execute('SELECT COUNT(*) FROM transactions WHERE component_id = ?', (id,)).fetchone()[0]
    if count > 0:
        flash('Cannot delete component because it has past transaction records!', 'error')
    else:
        conn.execute('DELETE FROM components WHERE id = ?', (id,))
        conn.commit()
        flash('Component deleted safely.', 'success')
        
    conn.close()
    return redirect(url_for('manage_components'))

@app.route('/export')
def export_csv():
    conn = get_db_connection()
    txs = conn.execute('''
        SELECT t.id, t.sr_number, tech.name as technician_name, comp.name as component_name, 
               t.quantity, t.status, t.issued_at, t.updated_at
        FROM transactions t
        JOIN technicians tech ON t.technician_id = tech.id
        JOIN components comp ON t.component_id = comp.id
        ORDER BY t.issued_at DESC
    ''').fetchall()
    conn.close()
    
    # Generate CSV string iteratively
    def generate():
        data = StringIO()
        writer = csv.writer(data)
        
        # Write Title Header
        writer.writerow(('Transaction ID', 'SR Number', 'Technician', 'Component', 'Quantity', 'Status', 'Issued Date', 'Last Updated'))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        
        # Write Data
        for tx in txs:
            writer.writerow((tx['id'], tx['sr_number'], tx['technician_name'], tx['component_name'], tx['quantity'], tx['status'], tx['issued_at'], tx['updated_at']))
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
            
    response = Response(generate(), mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename='vguard_transactions.csv')
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
