all:

install: epever.service logtracer_csv.py SolarTracer.py
	install -m 755 logtracer_csv.py /usr/bin/
	install -m 644 SolarTracer.py /usr/bin/
	install -m 644 epever.service /etc/systemd/system

start:
	 systemctl daemon-reload
	 systemctl enable epever
	 systemctl start epever
	 systemctl status epever

stop:
	 systemctl stop epever
	 systemctl status epever
