from datetime import datetime
import sqlite3
from flask import Flask, jsonify, render_template_string, request
from twilio.rest import Client

app = Flask(__name__)

# --- Twilio Configuration ---
# Replace these with your actual Twilio credentials
TWILIO_ACCOUNT_SID = "your_account_sid_here"
TWILIO_AUTH_TOKEN = "your_auth_token_here"
TWILIO_PHONE_NUMBER = "your_twilio_phone_number_here"


# --- Database Setup (SQLite - Built-in & Zero Config) ---
def init_db():
  conn = sqlite3.connect("pharmacy.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)
  # Insert sample data if the table is empty
  cursor.execute("SELECT COUNT(*) FROM medicines")
  if cursor.fetchone()[0] == 0:
    cursor.execute(
        "INSERT INTO medicines VALUES ('MED001', 'Paracetamol 500mg',"
        " '2024-05-10', 50.0)"
    )
    cursor.execute(
        "INSERT INTO medicines VALUES ('MED002', 'Amoxicillin 250mg',"
        " '2028-12-31', 120.0)"
    )
    conn.commit()
  conn.close()


init_db()


def send_expiry_sms(customer_phone, medicine_name, expiry_date):
  """Sends an SMS alert if Twilio credentials are configured."""
  if (
      TWILIO_ACCOUNT_SID == "your_account_sid_here"
      or not TWILIO_ACCOUNT_SID
  ):
    print(
        f"[SIMULATION] Twilio not configured. Expiry SMS for {medicine_name}"
        f" would be sent to {customer_phone}."
    )
    return False

  try:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message_body = (
        f"ALERT: Dear Customer, the medicine '{medicine_name}' you purchased"
        f" expired on {expiry_date}. Please do not consume it and return it"
        " immediately."
    )
    client.messages.create(
        body=message_body, from_=TWILIO_PHONE_NUMBER, to=customer_phone
    )
    print("SMS sent successfully via Twilio!")
    return True
  except Exception as e:
    print(f"Failed to send SMS: {e}")
    return False


# --- Frontend HTML & JavaScript Interface ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pharmacy Management System</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; margin: 0; padding: 50px; display: flex; justify-content: center; }
        .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 400px; }
        h2 { color: #2c3e50; text-align: center; margin-bottom: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; color: #333; }
        input { width: 100%; padding: 10px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 5px; font-size: 14px; }
        button { background: #3498db; color: white; border: none; padding: 12px; width: 100%; border-radius: 5px; font-size: 16px; cursor: pointer; font-weight: bold; transition: background 0.3s; }
        button:hover { background: #2980b9; }
        #result { margin-top: 20px; padding: 15px; border-radius: 5px; display: none; font-size: 14px; line-height: 1.5; }
        .success { background: #e8f8f5; color: #117a65; border: 1px solid #a3e4d7; }
        .warning { background: #fdebd0; color: #b9770e; border: 1px solid #f9e79f; }
        .error { background: #fadbd8; color: #922b21; border: 1px solid #f5b7b1; }
        .note { font-size: 12px; color: #7f8c8d; margin-top: 15px; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h2>💊 Pharmacy Checkout</h2>
        <div class="form-group">
            <label>Medicine ID:</label>
            <input type="text" id="medicineId" value="MED001" placeholder="e.g. MED001">
        </div>
        <div class="form-group">
            <label>Customer Phone Number:</label>
            <input type="text" id="customerPhone" value="+1234567890" placeholder="e.g. +1234567890">
        </div>
        <button onclick="buyMedicine()">Complete Purchase</button>
        <div id="result"></div>
        <div class="note">Tip: Use <b>MED001</b> (Expired) or <b>MED002</b> (Fresh).</div>
    </div>

    <script>
        async function buyMedicine() {
            const medicineId = document.getElementById('medicineId').value;
            const customerPhone = document.getElementById('customerPhone').value;
            const resultDiv = document.getElementById('result');

            resultDiv.style.display = 'none';

            try {
                const response = await fetch('/api/purchase', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ medicine_id: medicineId, customer_phone: customerPhone })
                });
                const data = await response.json();

                resultDiv.style.display = 'block';
                if (response.ok) {
                    if (data.is_expired) {
                        resultDiv.className = 'warning';
                        resultDiv.innerHTML = `<strong>⚠️ EXPIRED MEDICINE ALERT!</strong><br>` +
                                              `Medicine: <b>${data.medicine_name}</b><br>` +
                                              `Expired On: ${data.expiry_date}<br>` +
                                              `<em>${data.message}</em>`;
                    } else {
                        resultDiv.className = 'success';
                        resultDiv.innerHTML = `<strong>✅ Purchase Successful!</strong><br>` +
                                              `Medicine: <b>${data.medicine_name}</b><br>` +
                                              `Expiry: ${data.expiry_date}<br>` +
                                              `${data.message}`;
                    }
                } else {
                    resultDiv.className = 'error';
                    resultDiv.innerHTML = `<strong>Error:</strong> ${data.error}`;
                }
            } catch (err) {
                resultDiv.style.display = 'block';
                resultDiv.className = 'error';
                resultDiv.innerHTML = `<strong>Request Failed:</strong> ${err.message}`;
            }
        }
    </script>
</body>
</html>
"""


# --- Backend API Routes ---
@app.route("/")
def home():
  # Renders the HTML frontend directly from Python
  return render_template_string(HTML_TEMPLATE)


@app.route("/api/purchase", methods=["POST"])
def purchase():
  data = request.get_json()
  medicine_id = data.get("medicine_id")
  customer_phone = data.get("customer_phone")

  if not medicine_id or not customer_phone:
    return (
        jsonify({"error": "Medicine ID and Customer Phone are required."}),
        400,
    )

  # Check Database
  conn = sqlite3.connect("pharmacy.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT name, expiry_date, price FROM medicines WHERE id = ?",
      (medicine_id,),
  )
  row = cursor.fetchone()
  conn.close()

  if not row:
    return jsonify({"error": "Medicine ID not found in database."}), 404

  name, expiry_str, price = row

  # Expiry date validation logic
  expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
  current_date = datetime.now().date()
  is_expired = current_date > expiry_date

  response_data = {
      "status": "success",
      "medicine_name": name,
      "expiry_date": expiry_str,
      "is_expired": is_expired,
  }

  # If product is expired, trigger SMS
  if is_expired:
    sms_sent = send_expiry_sms(customer_phone, name, expiry_str)
    response_data["sms_alert_sent"] = sms_sent
    response_data["message"] = (
        "Product is EXPIRED! An SMS warning has been dispatched to the"
        " customer."
    )
  else:
    response_data["message"] = (
        "Transaction complete. The product is fresh and safe."
    )

  return jsonify(response_data), 200


if __name__ == "__main__":
  app.run(debug=True, port=5000)
