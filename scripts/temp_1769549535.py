import os
import subprocess

# Creazione della dashboard in ~/panda/dashboard
os.makedirs(os.path.expanduser("~/panda/dashboard"), exist_ok=True)

# Creazione del file deamon.service per systemd
daemon_service_content = """
[Unit]
Description=Panda Dashboard Service
After=network.target

[Service]
User=panda
Group=panda
WorkingDirectory={0}
ExecStart=/usr/bin/python3 {1}
Restart=always

[Install]
WantedBy=multi-user.target
""".format(os.path.expanduser("~/panda/dashboard"), os.path.join(os.path.expanduser("~/panda/dashboard"), "panda-dashboard.py"))

with open("/etc/systemd/system/panda-dashboard.service", "w") as f:
    f.write(daemon_service_content)

# Aggiornamento di systemd e attivazione del servizio
subprocess.run(["sudo", "systemctl", "daemon-reload"])
subprocess.run(["sudo", "systemctl", "enable", "--now", "panda-dashboard"])

# Ottimizzazione della risposta per la stampa dell'IP locale
ip_addresses = subprocess.check_output("hostname -I").decode().strip()
print(f"""
1) Dashboard creata in ~/panda/dashboard

2) Per attivare esegui:
   sudo cp ~/panda/dashboard/panda-dashboard.service /etc/systemd/system/ && \\
   sudo systemctl daemon-reload && \\
   sudo systemctl enable --now panda-dashboard

3) Poi accedi a http://"" + ip_addresses + """5000

4) Trova IP con: hostname -I
""")