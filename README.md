# PsychoNotes 🧠

**Cross-platform CRM & Session Management System for Psychologists**

PsychoNotes is a specialized tool designed to streamline the workflow of practicing psychologists. It replaces fragmented paper notes with a unified, secure, and structured local database. Built with a focus on data privacy and professional stability.

---

### ✨ Detailed Feature Set

* **Advanced Client CRM:**
    * **Psychological Profiling:** Dedicated fields for temperament, character type, and perception styles allow for a deeper understanding of the client's personality structure.
    * **Anamnesis & Help Plan:** Specialized modules for long-term therapy planning and tracking historical background.
    * **Dynamic Request Management:** A flexible UI implementation that allows adding or removing multiple therapy requests on-the-fly without database conflicts.
* **Scientific Session Tracking:**
    * **Quantifiable Progress:** Use of initial and final state scores (0-10) to visually track therapeutic efficacy over time.
    * **Standardized Templates:** Pre-defined fields for "Meeting Location", "Weather" (environmental context), "Techniques used", and "Outcomes" to ensure no detail is missed.
* **Data Integrity & Security:**
    * **SQLite Backend:** Relational data mapping ensures that deleting a client safely handles all associated session notes.
    * **Instant Search:** Optimized lookup by full name, enabling quick navigation through large client bases.
    * **Total Privacy:** Zero cloud dependency. All sensitive data remains on the professional's device, fulfilling ethical requirements for data confidentiality.

### ⚙️ Technical Deep Dive

**1. Cross-Platform Engine (Kivy & Buildozer)**
The application utilizes the **Kivy** framework for hardware-accelerated graphics (OpenGL ES 2).
* **Buildozer Pipeline:** Specifically configured to handle Android permissions and packaging `sqlite3` binaries within the APK.
* **Adaptive Metrics:** Implementation of `kivy.metrics.dp` ensures the UI scales gracefully from a 6.7" smartphone to a desktop monitor.

**2. Database Architecture**
The system follows a relational model implemented in **SQLite**. 
* **Joins & Queries:** History screens utilize complex SQL JOINs to fetch client names alongside session data, optimizing memory usage.
* **Resource Handling:** Custom logic to detect `sys.frozen` state (PyInstaller) to correctly locate `.kv` UI files and the database path in compiled environments.

**3. UI/UX Logic**
* **Screen Management:** A robust `ScreenManager` implementation ensures smooth transitions and state persistence between the Client List and Session Notes.
* **Reactive Inputs:** Real-time data binding between Python properties (`StringProperty`, `NumericProperty`) and Kivy Language (`.kv`) files.

---

### 🛠 Technology Stack

* **Core:** Python 3.x
* **UI:** Kivy Framework (KV Language)
* **Database:** SQLite
* **Deployment:** Buildozer (Android APK), PyInstaller (Windows EXE)

---

### 🚀 Getting Started

#### Windows
1. Download the latest archive from the **Releases** section.
2. Unpack and run `PsychologistNotes.exe`.

#### Android
1. Download the `.apk` file from the **Releases** section.
2. Install it on your device (enable "Install from unknown sources").

---

### 📈 Future Roadmap
* **Modern Aesthetic:** Transitioning to a "pastel professional" UI theme.
* **Custom Templates:** User-defined session note structures.
* **Data Export:** Exporting client history to PDF/Excel.

---
*Developed by Efim Romanchenko (efrom-K) — bridging the gap between stable code and professional practice.*
