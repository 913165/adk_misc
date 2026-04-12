import sqlite3
from google.adk.agents.llm_agent import Agent

# ── Create DB and seed data on startup ───────────────────────────────────────
def init_db():
    conn = sqlite3.connect("clinic.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY,
        name TEXT,
        specialty TEXT,
        available INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT,
        patient_name TEXT,
        date TEXT,
        time TEXT,
        status TEXT DEFAULT 'Confirmed'
    )""")

    # Seed doctors if table is empty
    c.execute("SELECT COUNT(*) FROM doctors")
    if c.fetchone()[0] == 0:
        doctors = [
            (1, "Dr. Priya Sharma", "General Physician", 1),
            (2, "Dr. Rahul Mehta", "Dermatologist", 1),
            (3, "Dr. Anjali Desai", "Pediatrician", 1),
            (4, "Dr. Vikram Patil", "Orthopedic", 1),
            (5, "Dr. Sneha Kulkarni", "Dentist", 1),
            (6, "Dr. Amit Joshi", "Cardiologist", 1),
            (7, "Dr. Neha Gupta", "Gynecologist", 1),
            (8, "Dr. Sanjay Rao", "ENT Specialist", 1),
        ]
        c.executemany("INSERT INTO doctors VALUES (?,?,?,?)", doctors)

    conn.commit()
    conn.close()


init_db()

# ── Tool 1: Find doctors ────────────────────────────────────────────────────
def find_doctors(specialty: str) -> dict:
    """Finds available doctors by their specialty.

    Args:
        specialty: Medical specialty like "Dentist", "Cardiologist", "Pediatrician".
    """
    conn = sqlite3.connect("clinic.db")
    c = conn.cursor()
    c.execute(
        "SELECT name, specialty FROM doctors WHERE LOWER(specialty) LIKE LOWER(?) AND available = 1",
        (f"%{specialty}%",)
    )
    rows = c.fetchall()
    conn.close()

    if rows:
        return {"doctors": [{"name": r[0], "specialty": r[1]} for r in rows]}
    return {"error": f"No doctors found for '{specialty}'. Try: Dentist, Cardiologist, Pediatrician, Dermatologist, Orthopedic, ENT Specialist, Gynecologist, General Physician."}

# ── Tool 2: Book appointment ────────────────────────────────────────────────
def book_appointment(doctor_name: str, patient_name: str, date: str, time: str) -> dict:
    """Books an appointment with a doctor.

    Args:
        doctor_name: Full name of the doctor like "Dr. Priya Sharma".
        patient_name: Name of the patient.
        date: Appointment date like "2026-04-15".
        time: Appointment time like "10:30 AM".
    """
    conn = sqlite3.connect("clinic.db")
    c = conn.cursor()

    # Check doctor exists
    c.execute("SELECT name FROM doctors WHERE LOWER(name) = LOWER(?)", (doctor_name,))
    if not c.fetchone():
        conn.close()
        return {"error": f"Doctor '{doctor_name}' not found. Use find_doctors to search first."}

    # Check for double booking
    c.execute(
        "SELECT id FROM appointments WHERE LOWER(doctor_name) = LOWER(?) AND date = ? AND time = ? AND status = 'Confirmed'",
        (doctor_name, date, time)
    )
    if c.fetchone():
        conn.close()
        return {"error": f"{doctor_name} already has a booking at {time} on {date}. Try a different time."}

    c.execute(
        "INSERT INTO appointments (doctor_name, patient_name, date, time) VALUES (?,?,?,?)",
        (doctor_name, patient_name, date, time)
    )
    apt_id = c.lastrowid
    conn.commit()
    conn.close()

    return {
        "appointment_id": apt_id,
        "doctor": doctor_name,
        "patient": patient_name,
        "date": date,
        "time": time,
        "status": "Confirmed",
    }

# ── Tool 3: Cancel appointment ──────────────────────────────────────────────
def cancel_appointment(appointment_id: int) -> dict:
    """Cancels an existing appointment by its ID.

    Args:
        appointment_id: The appointment ID number like 1 or 2.
    """
    conn = sqlite3.connect("clinic.db")
    c = conn.cursor()

    c.execute("SELECT doctor_name, patient_name, date, time, status FROM appointments WHERE id = ?", (appointment_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        return {"error": f"Appointment #{appointment_id} not found."}

    if row[4] == "Cancelled":
        conn.close()
        return {"error": f"Appointment #{appointment_id} is already cancelled."}

    c.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()

    return {
        "appointment_id": appointment_id,
        "doctor": row[0],
        "patient": row[1],
        "date": row[2],
        "time": row[3],
        "status": "Cancelled",
        "message": "Appointment has been cancelled successfully.",
    }

# ── Agent ────────────────────────────────────────────────────────────────────
root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="Clinic booking assistant that finds doctors, books and cancels appointments.",
    instruction=(
        "You are a friendly clinic receptionist. Help patients with:\n"
        "- Finding doctors by specialty using find_doctors\n"
        "- Booking appointments using book_appointment\n"
        "- Cancelling appointments using cancel_appointment\n\n"
        "Always search for a doctor first before booking. "
        "Ask for the patient's name, preferred date and time before booking. "
        "Confirm details before finalizing."
    ),
    tools=[find_doctors, book_appointment, cancel_appointment],
)