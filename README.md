# 🕶️ The Network Godfather (عرّاب الشبكة)

> **"I'm gonna make your network an offer it can't refuse: Efficiency or Deactivation."**

## 📖 The Vision
In the era of 5G and complex microwave backhauls, **Static Reservation is a Crime.** While some nodes starve for capacity, others hoard unused E1s, Licenses, and Bandwidth like "Phantom Resources." 

**The Network Godfather** is a **Resource Sovereign Orchestrator**. It doesn't just monitor; it judges and redistributes network wealth. Developed from the heart of Djelfa to the world, it ensures that every Watt, License, and Byte is serving the network's growth, not sitting idle in a database.

## 🔄 The Lifecycle (The 4 Pillars)

### 1. 🔍 Deep Discovery
The "Scout" phase. The Godfather scans everything:
- **Physical:** TX Power, RSL, SME, E1/STM usage,CPRI,OTN ODU.
- **Processing:** CPU Load, **Memory Reserved**, and **Data Processing Units**.
- **Software:** **Licenses** (Fake used vs. Actual used), License Pools,Modulation Level License,Multi-Carrier.
- **Logic:** Bandwidth (28/56MHz) and Traffic patterns.

### 2. ⚖️ The Judgment
The "Audit" phase. Comparing **Reserved Capacity** vs. **Actual Reality**.
- Identifies **"Ghost Links"**: e.g., a link using 56MHz bandwidth with only 5% traffic load.
- Detects **"Zombie Memory"**: Reserved processing power for decommissioned BTS sites.
- Flags **"Fake Used"** licenses that are locked but idle.

### 3. 🔓 The Liberation
The "Action" phase.
- Notifies engineers with a clear ultimatum: **"Use it or Lose it."**
- Automatically releases idle E1s and Licenses into the **Global Resource Pool**.
- Consolidates power and bandwidth to create a **Power & License Bank**.

### 4. 📜 The Legacy
The "ROI" phase.
- Records every saved unit in a permanent **SQL Ledger**.
- Generates financial reports showing exactly how much **CAPEX/OPEX** was saved by recycling instead of buying.

## 🛠️ Key Features
- **Vendor Agnostic:** Custom adapters for Huawei (RTN/BTS), Nokia, and Ericsson.
- **Safety Protocol:** 15-day observation & 10-day "Cool-down" before final clean-up.
- **Intelligence Layer:** Predicts congestion and preemptively re-allocates freed resources.

## 🚀 Quick Start
```bash
# Clone the Godfather
git clone [https://github.com/Ahmed-Chaouli/network-godfather.git](https://github.com/your-username/network-godfather.git)
cd network-godfather

# Run the Audit for a specific region
python main.py --region "Paris" --action "audit"