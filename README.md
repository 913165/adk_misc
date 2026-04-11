```
python3 -m pip install -r requirements.txt
```

Here are the **Windows commands** to **check which process is using a port** and **kill it**.

---

# 1️⃣ Check which process is using a port

Example for **port 8080**:

```bat id="p7e4hc"
netstat -ano | findstr :8080
```

Output example:

```
TCP    0.0.0.0:8080     0.0.0.0:0     LISTENING     36124
```

👉 Last number (`36124`) = **PID (Process ID)**

---

# 2️⃣ Kill the process using PID

```bat id="5l0ah1"
taskkill /PID 36124 /F
```

`/F` = force kill

---

# 3️⃣ One-line command (find + kill)

```bat id="g7e6fg"
for /f "tokens=5" %a in ('netstat -ano ^| findstr :8080') do taskkill /PID %a /F
```

---

# 4️⃣ Check process name from PID (optional)

```bat id="3ns0m5"
tasklist | findstr 36124
```

---

# Example workflow

```bat id="c4v5nn"
netstat -ano | findstr :8080
taskkill /PID 36124 /F
```

---
