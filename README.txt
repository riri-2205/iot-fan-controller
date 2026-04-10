================================================================
  Wi-Fi Based Smart Ceiling Fan Control System
  Using Multi-Agent AI
  EE427 - Computer Networks Mini Project
  National Institute of Technology Karnataka
================================================================

Team Members:
  Rithika S (Roll No. 231EE147)
  Rohit  (Roll No. 231EE148)
  Sanegha Sakhare  (Roll No. 231EE151)
  Sanjana Dalal  (Roll No. 231EE152)

Guide: Dr. K. P. Vittal
Department of Electrical and Electronics Engineering
================================================================

CONTENTS OF THIS ZIP FILE
--------------------------
  agents.py               -- Multi-Agent AI controller (4 AI agents)
  mqtt_handler.py         -- MQTT communication handler
  app.py                  -- Flask web server and main controller
  dashboard.html          -- Web browser user interface
  esp32_fan_controller.ino -- ESP32 firmware code for Wokwi simulator
  wokwi_link.txt          -- Link to the Wokwi ESP32 simulation
  screenshots/            -- PDF containing result screenshots
  

================================================================

WHAT THIS PROJECT DOES
-----------------------
This project demonstrates a complete IoT system for controlling
a ceiling fan over Wi-Fi using a web browser. The fan has 4
operating speeds: OFF, LOW, MEDIUM, and HIGH.

The system has two modes:
  1. MANUAL MODE  -- User clicks buttons on the webpage to
                     directly control the fan speed.
  2. AUTO MODE    -- AI agents automatically decide the fan
                     speed every 5 seconds based on simulated
                     temperature and time of day.

Commands are sent using the MQTT protocol (IoT standard) to a
public broker (HiveMQ), which forwards them to a simulated
ESP32 microcontroller on Wokwi. The ESP32 lights up LEDs to
show the current fan speed.

================================================================

HOW TO RUN THE PROJECT
-----------------------

STEP 1 -- Install required libraries (only needed once)
  Open Command Prompt and type:
    pip install flask flask-cors paho-mqtt
  Press Enter and wait for installation to complete.

STEP 2 -- Start the web server
  Open Command Prompt and type:
    cd C:\SmartFan
    python app.py
  Leave this window open. Do not close it.

STEP 3 -- Open the web dashboard
  Open any web browser (Chrome, Edge, Firefox).
  Go to:
    http://localhost:5000
  The Smart Fan Control dashboard will appear.

STEP 4 -- Open the Wokwi hardware simulator
  Open the link inside wokwi_link.txt in your browser.
  Click the green Play button (triangle) to start simulation.
  Wait about 30 seconds for the ESP32 to connect.

STEP 5 -- Test the system
  - In MANUAL mode: Click OFF / LOW / MEDIUM / HIGH buttons
    and watch the LEDs change on Wokwi in real time.
  - In AUTO mode: Click the AUTO (AI) button and watch the
    AI agents automatically decide the speed every 5 seconds.

STEP 6 -- Stop the server
  Go to the Command Prompt running app.py
  Press Ctrl + C to stop the server.

================================================================

SYSTEM REQUIREMENTS
--------------------
  - Windows 10 or later
  - Python 3.8 or later
  - Internet connection (for MQTT broker and Wokwi)
  - Any modern web browser

================================================================

MQTT COMMUNICATION DETAILS
---------------------------
  Protocol  : MQTT v3.1.1
  Broker    : broker.hivemq.com
  Port      : 1883
  Topic (Publish)   : iot/smartfan/control
  Topic (Subscribe) : iot/smartfan/status

  Message Format:
  {
      "device": "fan1",
      "speed": "HIGH",
      "mode": "auto",
      "ts": 1718000000
  }

================================================================

AI AGENT LOGIC SUMMARY
------------------------
  Temperature Agent:
    Below 25C         --> OFF
    25C to 30C        --> LOW
    30C to 35C        --> MEDIUM
    35C and above     --> HIGH

  User Preference Agent:
    Night (10pm-6am)  --> Prefer LOW (quiet operation)
    Daytime           --> No preference

  Energy Optimization Agent:
    If vote is HIGH   --> Reduce to MEDIUM (save energy)
    Otherwise         --> No change

  Coordinator Agent:
    Combines all agent votes and resolves conflicts
    to produce the final fan speed command.

================================================================

LED MAPPING ON ESP32 (Wokwi)
------------------------------
  OFF    --> All LEDs off       (0 LEDs)
  LOW    --> Blue LED on        (1 LED)
  MEDIUM --> Blue + Green on    (2 LEDs)
  HIGH   --> Blue + Green + Red (3 LEDs)

================================================================