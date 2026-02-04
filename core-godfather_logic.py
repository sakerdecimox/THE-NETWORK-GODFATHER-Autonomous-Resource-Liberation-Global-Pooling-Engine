import sqlite3
import logging
import csv
import os
from datetime import datetime, date
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

# ==============================================================================
#  LinkMind v98.0 - THE CFO EDITION (Architectural Maturity)
#  -----------------------------------------------------------------------------
#  1. SEPARATION OF CONCERNS: DatabaseManager handles SQL, Godfather handles Logic.
#  2. REDEMPTION LOGIC: 3 consecutive clean days required to exit probation.
#  3. DRY-RUN AUDIT: Logs "Potential Actions" to CSV for review.
#  4. REPORTING: Exports financial data to CSV.
# ==============================================================================

CONFIG = {
    'DB_PATH': "LinkMind_Network.db",
    'LOG_FILE': "godfather.log",
    'DRY_RUN_FILE': "audit_simulation.csv",
    'FINANCIAL_FILE': "financial_report.csv",
    'PROBATION_DAYS': 15,
    'REDEMPTION_DAYS': 3, # Clean days required for pardon
    'COSTS': {'LICENSE_MBPS': 10.0, 'BW_MHZ': 20.0}
}

logging.basicConfig(filename=CONFIG['LOG_FILE'], level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger("CFO")

# --- Custom Errors ---
class UnsupportedVendorError(Exception): pass

# --- Data Structures ---
@dataclass
class NodeData:
    id: str; vendor: str; bandwidth: int; throughput: float
    license_reserved: int; license_actual: int; admin_status: str

@dataclass
class Verdict:
    status: str; offense_code: str; wasted_qty: float
    saving_value: float; details: str

# --- 1. Database Manager (Separation of Concerns) ---
class DatabaseManager:
    """Solely responsible for SQLite interactions"""
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_tables()

    def _get_conn(self): return sqlite3.connect(self.db_path)

    def _init_tables(self):
        with self._get_conn() as conn:
            # Added clean_streak to track innocent days
            conn.execute('''CREATE TABLE IF NOT EXISTS probation_list 
                          (link_id TEXT PRIMARY KEY, offense_code TEXT, start_date TEXT, 
                           last_seen TEXT, clean_streak INTEGER DEFAULT 0)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS financial_ledger 
                          (id INTEGER PRIMARY KEY, date TEXT, link_id TEXT, 
                           action_taken TEXT, recovered_value REAL)''')

    def get_probation_record(self, link_id):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT start_date, clean_streak FROM probation_list WHERE link_id=?", (link_id,))
            return cursor.fetchone()

    def add_probation(self, link_id, offense):
        today = date.today().isoformat()
        with self._get_conn() as conn:
            conn.execute("INSERT INTO probation_list VALUES (?, ?, ?, ?, 0)", 
                         (link_id, offense, today, today))

    def update_probation_guilty(self, link_id):
        """Update last seen date and RESET clean streak"""
        today = date.today().isoformat()
        with self._get_conn() as conn:
            conn.execute("UPDATE probation_list SET last_seen=?, clean_streak=0 WHERE link_id=?", 
                         (today, link_id))

    def update_probation_innocent(self, link_id):
        """Increment clean streak"""
        with self._get_conn() as conn:
            conn.execute("UPDATE probation_list SET clean_streak = clean_streak + 1 WHERE link_id=?", 
                         (link_id,))

    def delete_probation(self, link_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM probation_list WHERE link_id=?", (link_id,))

    def add_ledger_entry(self, link_id, action, value):
        today = date.today().isoformat()
        with self._get_conn() as conn:
            conn.execute("INSERT INTO financial_ledger (date, link_id, action_taken, recovered_value) VALUES (?, ?, ?, ?)",
                         (today, link_id, action, value))
            
    def get_total_savings(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(recovered_value) FROM financial_ledger")
            return cursor.fetchone()[0] or 0.0

    def export_ledger_csv(self, filename):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM financial_ledger")
            rows = cursor.fetchall()
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Date", "Link ID", "Action", "Value ($)"])
                writer.writerows(rows)

# --- 2. Vendor Adapters (Unchanged) ---
class VendorAdapter(ABC):
    @abstractmethod
    def generate_license_script(self, link_id, new_capacity): pass
    @abstractmethod
    def generate_bandwidth_script(self, link_id, new_bw): pass

class HuaweiAdapter(VendorAdapter):
    def generate_license_script(self, link_id, new_capacity):
        return f"// HUAWEI: license-group modify capacity {int(new_capacity)}"
    def generate_bandwidth_script(self, link_id, new_bw):
        return f"// HUAWEI: interface microwave-link -> channel-bandwidth {new_bw}mhz"
        
class CommandFactory:
    @staticmethod
    def get_adapter(vendor_name: str):
        if vendor_name.lower() == 'huawei': return HuaweiAdapter()
        raise UnsupportedVendorError(f"Vendor '{vendor_name}' not supported")

# --- 3. The Godfather (Business Logic) ---
class TheGodfather:
    def __init__(self, dry_run=False):
        self.db = DatabaseManager(CONFIG['DB_PATH']) # Using the new Manager
        self.dry_run = dry_run
        
        # Prepare audit file for dry-run
        if self.dry_run:
            with open(CONFIG['DRY_RUN_FILE'], 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Link ID", "Verdict", "Potential Saving", "Script Draft"])

    def audit_node(self, node: NodeData) -> Verdict:
        # (Same logic as before)
        verdict = Verdict("Innocent", "NONE", 0.0, 0.0, "Clean")
        if node.license_reserved > (node.license_actual * 1.5):
            wasted = node.license_reserved - node.license_actual
            verdict = Verdict("Guilty", "LICENSE_HOARDING", wasted, wasted * CONFIG['COSTS']['LICENSE_MBPS'], "License Bloat")
        elif node.bandwidth == 56 and node.throughput < 100:
            verdict = Verdict("Guilty", "SPECTRUM_WASTE", 28, 28 * CONFIG['COSTS']['BW_MHZ'], "Bandwidth Waste")
        return verdict

    def pass_judgment(self, node: NodeData, verdict: Verdict):
        # 1. Simulation Mode
        if self.dry_run:
            return self._log_simulation(node, verdict)

        # 2. Live Execution Mode
        if verdict.status == "Innocent":
            return self._handle_redemption(node)
        else:
            return self._enforce_probation(node, verdict)

    def _log_simulation(self, node: NodeData, verdict: Verdict):
        """Log simulation results to CSV"""
        script = "N/A"
        if verdict.status == "Guilty":
            try:
                adapter = CommandFactory.get_adapter(node.vendor)
                script = adapter.generate_license_script(node.id, node.license_actual) if "LICENSE" in verdict.offense_code else adapter.generate_bandwidth_script(node.id, 28)
            except: script = "Error generating script"

        with open(CONFIG['DRY_RUN_FILE'], 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now(), node.id, verdict.status, verdict.saving_value, script])
        
        return f"🧪 Dry-Run Logged for {node.id}: {verdict.status}"

    def _handle_redemption(self, node: NodeData):
        """Gradual Forgiveness Logic"""
        record = self.db.get_probation_record(node.id)
        if not record: return "✅ Clean (Not tracked)"
        
        clean_streak = record[1] + 1
        self.db.update_probation_innocent(node.id)
        
        if clean_streak >= CONFIG['REDEMPTION_DAYS']:
            self.db.delete_probation(node.id)
            logger.info(f"PARDONED [{node.id}]: Sustained innocence for {clean_streak} days.")
            return f"🕊️ PARDONED: Clean for {clean_streak} days. Removed from watchlist."
        
        return f"⚠️ IMPROVING: Clean Streak {clean_streak}/{CONFIG['REDEMPTION_DAYS']}"

    def _enforce_probation(self, node: NodeData, verdict: Verdict):
        record = self.db.get_probation_record(node.id)
        
        if record:
            start_date = date.fromisoformat(record[0])
            days_in_jail = (date.today() - start_date).days
            self.db.update_probation_guilty(node.id) # Reset clean streak on relapse
            
            if days_in_jail >= CONFIG['PROBATION_DAYS']:
                return self._execute_liquidation(node, verdict)
            return f"⚠️ SURVEILLANCE: Day {days_in_jail}. Streak Reset."
        else:
            self.db.add_probation(node.id, verdict.offense_code)
            return "📝 PROBATION STARTED"

    def _execute_liquidation(self, node: NodeData, verdict: Verdict):
        try:
            adapter = CommandFactory.get_adapter(node.vendor)
            script = adapter.generate_license_script(node.id, node.license_actual) # Simplified Example
            
            self.db.add_ledger_entry(node.id, verdict.offense_code, verdict.saving_value)
            self.db.delete_probation(node.id) # Case Closed
            
            logger.critical(f"EXECUTED [{node.id}]: Saved ${verdict.saving_value}")
            return f"⚖️ LIQUIDATED. Saved ${verdict.saving_value}"
        except Exception as e:
            return f"❌ ERROR: {str(e)}"

    def generate_cfo_report(self):
        if self.dry_run: return "Run in LIVE mode for report."
        
        self.db.export_ledger_csv(CONFIG['FINANCIAL_FILE'])
        total = self.db.get_total_savings()
        
        print("\n📊 CFO FINANCIAL REPORT")
        print("========================")
        print(f"Total Recovered Assets: ${total:,.2f}")
        print("Formula:")
        print(r"$$Savings_{Total} = \sum (Recovered\_BW \times 20\$) + (Recovered\_Lic \times 10\$)$$")
        print(f"Detailed CSV exported to: {CONFIG['FINANCIAL_FILE']}")
        print("========================")

# --- Execution ---
if __name__ == "__main__":
    # 1. Audit Trail Mode (Simulation)
    print("--- 🧪 Starting Dry Run ---")
    sim_godfather = TheGodfather(dry_run=True)
    node_bad = NodeData("17659-HW", "Huawei", 56, 10.0, 400, 50, "UP")
    print(sim_godfather.audit_node(node_bad)) # Just Auditing
    print(sim_godfather.pass_judgment(node_bad, sim_godfather.audit_node(node_bad))) # Judgment Sim
    print(f"Audit saved to {CONFIG['DRY_RUN_FILE']}")

    # 2. Live Mode
    print("\n--- 🔴 Starting Live Mode ---")
    live_godfather = TheGodfather(dry_run=False)
    
    # Simulating Redemption Scenario
    # Node was guilty, then became innocent multiple times
    live_godfather.pass_judgment(node_bad, Verdict("Guilty", "HOARDING", 100, 1000, "")) # Day 1 (Guilty)
    print("Day 1: Guilty -> Added to Probation")
    
    node_good = NodeData("17659-HW", "Huawei", 56, 400.0, 400, 390, "UP") # Became Good
    print(f"Day 2: {live_godfather.pass_judgment(node_good, Verdict('Innocent', '', 0, 0, ''))}")
    print(f"Day 3: {live_godfather.pass_judgment(node_good, Verdict('Innocent', '', 0, 0, ''))}")
    print(f"Day 4: {live_godfather.pass_judgment(node_good, Verdict('Innocent', '', 0, 0, ''))}") # Should be pardoned here
    
    live_godfather.generate_cfo_report()