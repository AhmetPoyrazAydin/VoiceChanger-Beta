"""
app.py

This Python script uses Flask to serve a web-based voice changer application.
When you run this file, it will start a local server (http://localhost:5000/) and open
your default web browser automatically. The app features a dark theme, drag-and-drop
audio file loading, microphone input with a toggleable delay effect, and real-time
waveform visualization.

Usage:
    1. Run this script: python app.py
    2. Your default web browser will open the voice changer app.
    3. Click "Start Microphone" to enable microphone input.
    4. Optionally, drag and drop an audio file into the drop zone to load an alternate voice.
    5. Use "Toggle Delay" to enable a slight delay effect (echo) on your microphone input.
    6. Click "Play Dropped Audio" to listen to the loaded audio file.

This app runs in modern browsers that support the Web Audio API.
"""

from flask import Flask, render_template_string
import webbrowser
import threading

app = Flask(__name__)

# The HTML, CSS, and JavaScript content for the voice changer web app.
# It includes advanced dark theme styling, a drag & drop area,
# full-screen handling, microphone input with delay effect, and waveform visualization.
html_content = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PozStudio VoiceChanger</title>
  <style>
    /* Advanced Dark Theme using CSS variables */
    :root {
      --bg-color: #121212;
      --secondary-bg: #1e1e1e;
      --text-color: #ffffff;
      --accent-color: #bb86fc;
      --button-bg: #333333;
      --button-hover: #444444;
      --dropzone-border: #444444;
    }
    /* Reset and base styles */
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      background-color: var(--bg-color);
      color: var(--text-color);
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }
    header {
      background-color: var(--secondary-bg);
      padding: 20px;
      text-align: center;
      border-bottom: 2px solid var(--accent-color);
    }
    header h1 {
      font-size: 2.5rem;
    }
    header span {
      font-size: 1.2rem;
      color: var(--accent-color);
    }
    main {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      position: relative;
      padding: 20px;
    }
    /* Drag & Drop Zone */
    #dropZone {
      border: 2px dashed var(--dropzone-border);
      padding: 40px;
      text-align: center;
      border-radius: 10px;
      margin-bottom: 20px;
      width: 80%;
      max-width: 600px;
      transition: background-color 0.3s;
    }
    #dropZone.dragover {
      background-color: var(--secondary-bg);
    }
    /* Control buttons */
    .controls {
      display: flex;
      gap: 15px;
      margin: 10px;
      flex-wrap: wrap;
      justify-content: center;
    }
    button {
      background-color: var(--button-bg);
      border: none;
      color: var(--text-color);
      padding: 10px 20px;
      font-size: 1rem;
      border-radius: 5px;
      cursor: pointer;
      transition: background-color 0.3s, transform 0.2s;
    }
    button:hover {
      background-color: var(--button-hover);
      transform: scale(1.05);
    }
    button:disabled {
      background-color: #555;
      cursor: not-allowed;
    }
    /* Waveform Visualization Canvas */
    #waveformCanvas {
      width: 80%;
      max-width: 600px;
      height: 100px;
      background-color: var(--secondary-bg);
      border-radius: 10px;
      margin-top: 20px;
    }
    footer {
      background-color: var(--secondary-bg);
      text-align: center;
      padding: 10px;
      border-top: 2px solid var(--accent-color);
      font-size: 0.8rem;
    }
  </style>
</head>
<body>
  <header>
    <h1>PozStudio <span>VoiceChanger</span></h1>
  </header>
  <main>
    <!-- Drag & Drop Area for Audio File -->
    <div id="dropZone">Drag & drop an audio file here to use as an alternate voice</div>
    <!-- Control Buttons -->
    <div class="controls">
      <button id="startMicBtn" title="Start microphone input">Start Microphone</button>
      <button id="stopMicBtn" title="Stop microphone input" disabled>Stop Microphone</button>
      <button id="toggleDelayBtn" title="Toggle delayed playback of your voice" disabled>Toggle Delay</button>
      <button id="playAudioBtn" title="Play the dropped audio file" disabled>Play Dropped Audio</button>
    </div>
    <!-- Canvas for live waveform visualization -->
    <canvas id="waveformCanvas"></canvas>
    <!-- Status messages displayed to the user -->
    <p id="statusMessage"></p>
  </main>
  <footer>
    &copy; 2025 PozStudio. All rights reserved.
  </footer>
  <script>
    // This script handles audio processing via the Web Audio API.
    // It captures microphone input, allows an audio file to be loaded via drag & drop,
    // toggles a delay (echo) effect on the microphone input, and visualizes the waveform.
    // It runs on modern browsers that support the Web Audio API.

    // Global variables for AudioContext and nodes
    let audioContext;
    let micStream;
    let micSource;
    let delayNode;
    let analyserNode;
    let droppedAudioBuffer = null;
    let droppedAudioSource = null;
    let isDelayEnabled = false;
    let animationId;

    // Get references to UI elements
    const startMicBtn = document.getElementById('startMicBtn');
    const stopMicBtn = document.getElementById('stopMicBtn');
    const toggleDelayBtn = document.getElementById('toggleDelayBtn');
    const playAudioBtn = document.getElementById('playAudioBtn');
    const dropZone = document.getElementById('dropZone');
    const statusMessage = document.getElementById('statusMessage');
    const canvas = document.getElementById('waveformCanvas');
    const canvasCtx = canvas.getContext('2d');

    // Request full-screen mode (triggered on first user interaction)
    function goFullscreen() {
      if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen();
      }
    }

    // --- Drag & Drop Handlers ---
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', (e) => {
      dropZone.classList.remove('dragover');
    });
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        const file = files[0];
        if (file.type.startsWith('audio/')) {
          const reader = new FileReader();
          reader.onload = function(evt) {
            const arrayBuffer = evt.target.result;
            // Create AudioContext if not already created
            if (!audioContext) {
              audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            audioContext.decodeAudioData(arrayBuffer, function(buffer) {
              droppedAudioBuffer = buffer;
              statusMessage.textContent = "Audio file loaded.";
              playAudioBtn.disabled = false;
            }, function(e) {
              console.error("Error decoding audio file", e);
              statusMessage.textContent = "Error decoding audio file.";
            });
          };
          reader.readAsArrayBuffer(file);
        } else {
          statusMessage.textContent = "Please drop a valid audio file.";
        }
      }
    });

    // --- Waveform Visualization ---
    function drawWaveform() {
      animationId = requestAnimationFrame(drawWaveform);
      const bufferLength = analyserNode.fftSize;
      const dataArray = new Uint8Array(bufferLength);
      analyserNode.getByteTimeDomainData(dataArray);
      canvasCtx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg-color');
      canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
      canvasCtx.lineWidth = 2;
      canvasCtx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent-color');
      canvasCtx.beginPath();
      const sliceWidth = canvas.width / bufferLength;
      let x = 0;
      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = (v * canvas.height) / 2;
        if (i === 0) {
          canvasCtx.moveTo(x, y);
        } else {
          canvasCtx.lineTo(x, y);
        }
        x += sliceWidth;
      }
      canvasCtx.lineTo(canvas.width, canvas.height / 2);
      canvasCtx.stroke();
    }

    // --- Microphone Input Handling ---
    async function startMicrophone() {
      try {
        // Create AudioContext if not already created
        if (!audioContext) {
          audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        micStream = stream;
        micSource = audioContext.createMediaStreamSource(stream);

        // Create a DelayNode for the delayed playback effect (initial delay = 0.2 sec)
        delayNode = audioContext.createDelay();
        delayNode.delayTime.value = 0.2;

        // Create an AnalyserNode for visualization
        analyserNode = audioContext.createAnalyser();
        analyserNode.fftSize = 2048;

        // Connect the microphone source to the analyser node
        micSource.connect(analyserNode);

        // Route the microphone either through the delay or directly to the destination
        if (isDelayEnabled) {
          micSource.connect(delayNode).connect(audioContext.destination);
        } else {
          micSource.connect(audioContext.destination);
        }

        stopMicBtn.disabled = false;
        toggleDelayBtn.disabled = false;
        statusMessage.textContent = "Microphone started.";
        drawWaveform();
        goFullscreen();  // Request full-screen mode on first interaction
      } catch (error) {
        console.error("Error accessing microphone", error);
        statusMessage.textContent = "Error accessing microphone.";
      }
    }

    function stopMicrophone() {
      if (micStream) {
        micStream.getTracks().forEach(track => track.stop());
      }
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
      stopMicBtn.disabled = true;
      toggleDelayBtn.disabled = true;
      statusMessage.textContent = "Microphone stopped.";
    }

    // --- Delay Toggle ---
    function toggleDelay() {
      isDelayEnabled = !isDelayEnabled;
      if (micSource) {
        micSource.disconnect();
        if (isDelayEnabled) {
          micSource.connect(delayNode).connect(audioContext.destination);
          statusMessage.textContent = "Delay enabled.";
        } else {
          micSource.connect(audioContext.destination);
          statusMessage.textContent = "Delay disabled.";
        }
      }
    }

    // --- Play Dropped Audio File ---
    function playDroppedAudio() {
      if (droppedAudioBuffer) {
        if (droppedAudioSource) {
          droppedAudioSource.stop();
        }
        droppedAudioSource = audioContext.createBufferSource();
        droppedAudioSource.buffer = droppedAudioBuffer;
        droppedAudioSource.connect(audioContext.destination);
        droppedAudioSource.start();
        statusMessage.textContent = "Playing dropped audio.";
      }
    }

    // --- Button Event Listeners ---
    startMicBtn.addEventListener('click', startMicrophone);
    stopMicBtn.addEventListener('click', stopMicrophone);
    toggleDelayBtn.addEventListener('click', toggleDelay);
    playAudioBtn.addEventListener('click', playDroppedAudio);

    // Resize the canvas to fit its container
    function resizeCanvas() {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
    }
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
  </script>
</body>
</html>"""


@app.route("/")
def index():
    # Render the HTML content for the voice changer app
    return render_template_string(html_content)


def open_browser():
    # Automatically open the default web browser to the local server URL
    webbrowser.open("http://localhost:5000/", new=2)


if __name__ == "__main__":
    # Start the Flask app and, after a short delay, open the browser
    threading.Timer(1, open_browser).start()
    app.run(port=5000)
