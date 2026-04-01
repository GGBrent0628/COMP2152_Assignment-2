"""
Author: Brent Joshua Samson
Assignment: #2
Description: Port Scanner — A tool that scans a target machine for open network ports
"""

# Import the required modules
import socket
import threading
import sqlite3
import os
import platform
import datetime

# Print Python version and OS name
print("Python Version:", platform.python_version())
print("Operating System:", os.name)


# Dictionary mapping port numbers to their common service names
common_ports = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    3306: "MySQL",
    3389: "RDP",
    8080: "HTTP-Alt"
}


class NetworkTool:

    def __init__(self, target):
        self.__target = target

    # Q3: What is the benefit of using @property and @target.setter?
    # Using @property and @target.setter allows controlled access to the private
    # attribute self.__target without exposing it directly. The setter lets us
    # add validation logic — in this case, rejecting empty strings — before
    # allowing a value to be stored. This is a key principle of encapsulation
    # in object-oriented programming: hiding internal data while controlling how
    # it is read and modified from outside the class.
    @property
    def target(self):
        return self.__target

    @target.setter
    def target(self, value):
        if value == "":
            print("Error: Target cannot be empty")
        else:
            self.__target = value

    def __del__(self):
        print("NetworkTool instance destroyed")


# Q1: How does PortScanner reuse code from NetworkTool?
# PortScanner inherits from NetworkTool using class PortScanner(NetworkTool),
# which means it automatically gets the __target attribute, the @property getter,
# the @target.setter with validation, and the destructor without rewriting any
# of that code. For example, when PortScanner calls super().__init__(target),
# it reuses NetworkTool's constructor to store and protect the target IP address.
class PortScanner(NetworkTool):

    def __init__(self, target):
        super().__init__(target)
        self.scan_results = []
        self.lock = threading.Lock()

    def __del__(self):
        print("PortScanner instance destroyed")
        super().__del__()

    def scan_port(self, port):
        # Q4: What would happen without try-except here?
        # Without try-except, any network error — such as a connection refused,
        # timeout, or unreachable host — would raise an unhandled exception and
        # crash the entire program mid-scan. Since we are running many threads
        # simultaneously, a single failure in one thread would bring everything
        # down. The try-except block lets each thread handle its own errors
        # gracefully and continue scanning the remaining ports.
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((self.target, port))
            if result == 0:
                status = "Open"
            else:
                status = "Closed"
            service_name = common_ports.get(port, "Unknown")
            self.lock.acquire()
            self.scan_results.append((port, status, service_name))
            self.lock.release()
        except socket.error as e:
            print(f"Error scanning port {port}: {e}")
        finally:
            sock.close()

    def get_open_ports(self):
        return [result for result in self.scan_results if result[1] == "Open"]

    # Q2: Why do we use threading instead of scanning one port at a time?
    # Threading allows multiple ports to be scanned at the same time in parallel,
    # which dramatically reduces the total time needed. Each port scan waits up
    # to 1 second for a timeout response, so scanning 1024 ports one at a time
    # could take over 17 minutes in the worst case. With threading, all 1024
    # scans run concurrently and the total time is roughly just 1 second.
    def scan_range(self, start_port, end_port):
        threads = []
        for port in range(start_port, end_port + 1):
            thread = threading.Thread(target=self.scan_port, args=(port,))
            threads.append(thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()


def save_results(target, results):
    try:
        conn = sqlite3.connect("scan_history.db")
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT,
            port INTEGER,
            status TEXT,
            service TEXT,
            scan_date TEXT
        )""")
        for result in results:
            cursor.execute(
                "INSERT INTO scans (target, port, status, service, scan_date) VALUES (?, ?, ?, ?, ?)",
                (target, result[0], result[1], result[2], str(datetime.datetime.now()))
            )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Database error: {e}")


def load_past_scans():
    try:
        conn = sqlite3.connect("scan_history.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scans")
        rows = cursor.fetchall()
        if not rows:
            print("No past scans found.")
        else:
            for row in rows:
                print(f"[{row[5]}] {row[1]} : Port {row[2]} ({row[4]}) - {row[3]}")
        conn.close()
    except sqlite3.Error:
        print("No past scans found.")


# ============================================================
# MAIN PROGRAM
# ============================================================
if __name__ == "__main__":

    # Get target IP
    target = input("Enter target IP address (press Enter for 127.0.0.1): ").strip()
    if target == "":
        target = "127.0.0.1"

    # Get start port
    start_port = None
    while start_port is None:
        try:
            start_port = int(input("Enter starting port (1-1024): "))
            if start_port < 1 or start_port > 1024:
                print("Port must be between 1 and 1024.")
                start_port = None
        except ValueError:
            print("Invalid input. Please enter a valid integer.")

    # Get end port
    end_port = None
    while end_port is None:
        try:
            end_port = int(input("Enter ending port (1-1024): "))
            if end_port < 1 or end_port > 1024:
                print("Port must be between 1 and 1024.")
                end_port = None
            elif end_port < start_port:
                print("End port must be greater than or equal to start port.")
                end_port = None
        except ValueError:
            print("Invalid input. Please enter a valid integer.")

    # Run the scan
    scanner = PortScanner(target)
    print(f"\nScanning {target} from port {start_port} to {end_port}...")
    scanner.scan_range(start_port, end_port)

    # Display results
    open_ports = scanner.get_open_ports()
    print(f"\n--- Scan Results for {target} ---")
    if open_ports:
        for port, status, service in open_ports:
            print(f"Port {port}: {status} ({service})")
    else:
        print("No open ports found.")
    print("------")
    print(f"Total open ports found: {len(open_ports)}")

    # Save to database
    save_results(target, scanner.scan_results)

    # Offer to show history
    show_history = input("\nWould you like to see past scan history? (yes/no): ").strip().lower()
    if show_history == "yes":
        load_past_scans()


# Q5: New Feature Proposal
# I would add an export feature that saves the scan results to a .csv file
# using a list comprehension to filter and format only the open ports into
# rows. This would make it easy to share or review results outside the terminal,
# and the list comprehension would efficiently build the CSV rows from the
# scan_results list in a single line.
# Diagram: See diagram_101201301.png in the repository root