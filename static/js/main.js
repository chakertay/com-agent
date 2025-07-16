// Global variables
let currentQuestion = 1;
let isRecording = false;
let speechRecognition = null;
let currentQuestionText = "";
let recognizedText = "";
const api_key = "MGU1MmM3NTQwYjllNGJhMGFhNWY4OWJiOTVjMTFmOGItMTc1MjY3MjQyMg==";
console.log("API KEY", api_key);
const API_CONFIG = {
    serverUrl: "https://api.heygen.com",
    apiKey: api_key,
};

// Global state
let sessionInfo = null;
let room = null;
let mediaStream = null;
let webSocket = null;
let sessionToken = null;

// DOM elements
const mediaElement = document.getElementById("mediaElement");
const taskInput = currentQuestionText;

const avatar = document.getElementById("avatar");

function setAvatarState(state) {
    if (!avatar) return;
    avatar.classList.remove("talking", "listening");
    if (state) {
        avatar.classList.add(state);
        if (state === "talking" || state === "listening") {
            avatar.style.display = "block";
            avatar
                .play()
                .catch((e) => console.log("Video autoplay prevented:", e));
        }
    } else {
        avatar.pause();
        avatar.style.display = "none";
    }
}

function startVoiceRecognition() {
    if (!isRecording) {
        isRecording = true;
        setAvatarState("listening");
        startRecording();
    }
}

function stopVoiceRecognition() {
    if (isRecording) {
        isRecording = false;
        setAvatarState("");
        stopRecording();
    }
}
//Get session token
async function getSessionToken() {
    const response = await fetch(
        `${API_CONFIG.serverUrl}/v1/streaming.create_token`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Api-Key": API_CONFIG.apiKey,
            },
        },
    );

    const data = await response.json();
    sessionToken = data.data.token;
}

// Connect WebSocket
async function connectWebSocket(sessionId) {
    const params = new URLSearchParams({
        session_id: sessionId,
        session_token: sessionToken,
        silence_response: false,
        opening_text: currentQuestionText,
        stt_language: "fr",
    });

    const wsUrl = `wss://${
        new URL(API_CONFIG.serverUrl).hostname
    }/v1/ws/streaming.chat?${params}`;

    webSocket = new WebSocket(wsUrl);

    // Handle WebSocket events
    webSocket.addEventListener("message", (event) => {
        const eventData = JSON.parse(event.data);
        console.log("Raw WebSocket event:", eventData.type);

        if (eventData.type === "avatar_stop_talking") {
            console.log("Heygen finished speaking");
            setAvatarState("listening");
            // Add a small delay to ensure audio processing is complete
            setTimeout(() => {
                if (!isRecording) {
                    startVoiceRecognition();
                }
            }, 500);
        }
    });
}

// Initialize assessment
async function initializeAssessment() {
    try {
        // Test speech recognition first
        const speechWorks = await testSpeechRecognition();
        if (!speechWorks) {
            showError(
                "Speech recognition is not available. Please use a supported browser (Chrome, Edge, Safari).",
            );
        }

        await analyzeCV();
        console.log("Analyzing CV...");
        await createHeygenSession();
        await startStreamingSession();
        console.log("Creating Heygen session...");
    } catch (error) {
        console.error("Error initializing assessment:", error);
        showError(
            "Échec de l'initialisation de l'évaluation. Veuillez réessayer.",
        );
    }
}

// Create new session
async function createHeygenSession() {
    if (!sessionToken) {
        await getSessionToken();
    }
    console.log("session token: ", sessionToken);
    const response = await fetch(`${API_CONFIG.serverUrl}/v1/streaming.new`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({
            quality: "high",
            avatar_name: "Wayne_20240711",
            voice: {
                voice_id: "4829d1907f1e48f3b7a7a1d0594abd7d",
                rate: 1.0,
            },
            version: "v2",
            video_encoding: "H264",
        }),
    });

    const data = await response.json();
    sessionInfo = data.data;
    console.log("session info: ", sessionInfo);

    // Create LiveKit Room
    room = new LivekitClient.Room({
        adaptiveStream: true,
        dynacast: true,
        videoCaptureDefaults: {
            resolution: LivekitClient.VideoPresets.h720.resolution,
        },
    });
    console.log("room: ", room);

    // Handle room events
    room.on(LivekitClient.RoomEvent.DataReceived, (message) => {
        const data = new TextDecoder().decode(message);
        const eventData = JSON.parse(data);
        if (eventData.type === "avatar_stop_talking") {
            console.log("Heygen finished speaking");
            // Add a small delay to ensure audio processing is complete
            setTimeout(() => {
                if (!isRecording) {
                    startVoiceRecognition();
                }
            }, 500);
        }
    });

    // Handle media streams
    mediaStream = new MediaStream();
    room.on(LivekitClient.RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === "video" || track.kind === "audio") {
            mediaStream.addTrack(track.mediaStreamTrack);
            if (
                mediaStream.getVideoTracks().length > 0 &&
                mediaStream.getAudioTracks().length > 0
            ) {
                mediaElement.srcObject = mediaStream;
            }
        }
    });

    // Handle media stream removal
    room.on(LivekitClient.RoomEvent.TrackUnsubscribed, (track) => {
        const mediaTrack = track.mediaStreamTrack;
        if (mediaTrack) {
            mediaStream.removeTrack(mediaTrack);
        }
    });

    // Handle room connection state changes
    room.on(LivekitClient.RoomEvent.Disconnected, (reason) => {});

    await room.prepareConnection(sessionInfo.url, sessionInfo.access_token);

    // Connect WebSocket after room preparation
    await connectWebSocket(sessionInfo.session_id);
}

// Start streaming session
async function startStreamingSession() {
    const startResponse = await fetch(
        `${API_CONFIG.serverUrl}/v1/streaming.start`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${sessionToken}`,
            },
            body: JSON.stringify({
                session_id: sessionInfo.session_id,
            }),
        },
    );

    // Connect to LiveKit room
    await room.connect(sessionInfo.url, sessionInfo.access_token);
}

// Send text to Heygen avatar
async function sendTextToHeygen(text, taskType = "repeat") {
    if (!sessionInfo) {
        return;
    }

    const response = await fetch(`${API_CONFIG.serverUrl}/v1/streaming.task`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({
            session_id: sessionInfo.session_id,
            text: text,
            task_type: taskType,
        }),
    });
}

// End Heygen Avatar session
async function closeHeygenSession() {
    if (!sessionInfo) {
        return;
    }

    const response = await fetch(`${API_CONFIG.serverUrl}/v1/streaming.stop`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({
            session_id: sessionInfo.session_id,
        }),
    });

    // Close WebSocket
    if (webSocket) {
        webSocket.close();
    }
    // Disconnect from LiveKit room
    if (room) {
        room.disconnect();
    }

    mediaElement.srcObject = null;
    sessionInfo = null;
    room = null;
    mediaStream = null;
    sessionToken = null;
}

// Analyze CV and get first question
async function analyzeCV() {
    try {
        /*
        const response = await fetch("/api/analyze_cv", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        });

        const data = await response.json();
        */
        
            currentQuestionText = " Bonjour comment je peut vous aider ?";
            displayQuestion(currentQuestionText);
            document.getElementById("loading-screen").style.display = "none";
            document.getElementById("assessment-interface").style.display =
                "block";
        
    } catch (error) {
        console.error("Error analyzing CV:", error);
        showError("Échec de l'analyse du CV. Veuillez réessayer.");
    }
}

// Display question
function displayQuestion(question) {
    const questionElement = document.getElementById("current-question-text");
    questionElement.textContent = question;
    currentQuestionText = question;
}

// Generate audio for question
async function generateQuestionAudio(text) {
    try {
        setAvatarState("talking");
        avatar.style.display = "block";

        const response = await fetch("/api/generate_audio", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ text: text }),
        });

        const data = await response.json();

        if (data.success) {
            const audioElement = document.getElementById("question-audio");
            audioElement.src = data.audio_url;
            audioElement.load();
            audioElement.play().catch((error) => {
                console.error("Error playing audio:", error);
                showError(
                    "Unable to play audio. Please check your browser settings.",
                );
            });

            audioElement.onended = () => {
                setAvatarState("listening");
                startVoiceRecognition();
            };
        } else {
            console.error("Failed to generate audio:", data.error);
        }
    } catch (error) {
        console.error("Error generating audio:", error);
    }
}

// Play question audio manually
function playQuestion() {
    const audioElement = document.getElementById("question-audio");
    if (audioElement.src) {
        audioElement.play().catch((error) => {
            console.error("Error playing audio:", error);
            showError(
                "Unable to play audio. Please check your browser settings.",
            );
        });
    }
}

// Start recording
async function startRecording() {
    console.log("startRecording called");
    try {
        if (!BrowserSpeechRecognition.isSupported()) {
            showError(
                "Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.",
            );
            isRecording = false;
            return;
        }
        console.log("Speech recognition is supported");

        // Request microphone permission first
        const hasPermission = await requestMicrophonePermission();
        if (!hasPermission) {
            isRecording = false;
            return;
        }

        if (!speechRecognition) {
            console.log("Initializing speechRecognition");
            speechRecognition = new BrowserSpeechRecognition();
            console.log("speechRecognition initialized", speechRecognition);

            try {
                speechRecognition.initialize();
                console.log("speechRecognition initialized successfully");
            } catch (initError) {
                console.error(
                    "Failed to initialize speech recognition:",
                    initError,
                );
                showError(
                    "Failed to initialize speech recognition. Please check your microphone permissions.",
                );
                isRecording = false;
                return;
            }

            speechRecognition.onResult = (result) => {
                const displayText =
                    result.final + (result.interim ? " " + result.interim : "");
                document.getElementById("transcribed-text").textContent =
                    displayText;

                // Show answer section when we have text
                if (displayText.trim()) {
                    document.getElementById("answer-section").style.display =
                        "block";
                    // Change indicator color to show we're getting input
                    const indicator = document.getElementById(
                        "recording-indicator",
                    );
                    if (indicator) {
                        indicator.style.color = "#28a745"; // Green when getting speech
                    }
                }

                if (result.isFinal && result.final.trim()) {
                    recognizedText = result.final;
                    document.getElementById("submit-btn").style.display =
                        "inline-block";
                    console.log("Final transcript:", result.final);
                }

                // Log interim results for debugging
                if (result.interim) {
                    console.log("Interim transcript:", result.interim);
                }
            };

            speechRecognition.onError = (error) => {
                console.error("Speech recognition error:", error);

                let errorMessage =
                    "Speech recognition error. Please try again.";
                let shouldRestart = false;

                if (error === "not-allowed") {
                    errorMessage =
                        "Microphone access denied. Please allow microphone access and try again.";
                    stopVoiceRecognition();
                } else if (error === "no-speech") {
                    console.log(
                        "No speech detected, restarting recognition...",
                    );
                    // Don't show error for no-speech, just restart
                    shouldRestart = true;
                } else if (error === "network") {
                    errorMessage =
                        "Network error. Please check your connection and try again.";
                    stopVoiceRecognition();
                } else if (error === "aborted") {
                    console.log("Speech recognition was aborted");
                    return; // Don't show error or restart
                } else {
                    stopVoiceRecognition();
                }

                if (shouldRestart && isRecording) {
                    // Restart recognition after a short delay
                    setTimeout(() => {
                        if (isRecording && speechRecognition) {
                            try {
                                speechRecognition.start();
                                console.log(
                                    "Speech recognition restarted after no-speech",
                                );
                            } catch (restartError) {
                                console.error(
                                    "Failed to restart speech recognition:",
                                    restartError,
                                );
                                stopVoiceRecognition();
                            }
                        }
                    }, 100);
                } else if (!shouldRestart) {
                    showError(errorMessage);
                }
            };

            speechRecognition.onEnd = () => {
                console.log("Speech recognition ended");

                // If we're still supposed to be recording, restart the recognition
                if (isRecording) {
                    setTimeout(() => {
                        if (isRecording && speechRecognition) {
                            try {
                                speechRecognition.start();
                                console.log(
                                    "Speech recognition restarted after ending",
                                );
                            } catch (restartError) {
                                console.error(
                                    "Failed to restart speech recognition:",
                                    restartError,
                                );
                                stopVoiceRecognition();
                            }
                        }
                    }, 100);
                }
            };
        }

        try {
            speechRecognition.start();
            console.log("Speech recognition started successfully");

            // Start microphone monitoring for visual feedback
            await startMicrophoneMonitoring();

            // Update UI to show recording state
            document.getElementById("record-btn").innerHTML =
                '<i class="fas fa-stop me-2"></i>Stop Recording';
            document
                .getElementById("record-btn")
                .classList.remove("btn-danger");
            document.getElementById("record-btn").classList.add("btn-warning");
            document.getElementById("recording-indicator").style.display =
                "block";
            document.getElementById("recording-indicator").style.color =
                "#dc3545"; // Start with red
        } catch (startError) {
            console.error("Failed to start speech recognition:", startError);
            showError(
                "Failed to start speech recognition. Please check your microphone permissions.",
            );
            isRecording = false;
        }
    } catch (error) {
        console.error("Error in startRecording:", error);
        showError(
            "Unable to start speech recognition. Please check your browser permissions.",
        );
        isRecording = false;
    }
}

// Stop recording
function stopRecording() {
    if (speechRecognition && isRecording) {
        try {
            speechRecognition.stop();
            console.log("Speech recognition stopped");
        } catch (error) {
            console.error("Error stopping speech recognition:", error);
        }

        isRecording = false;

        // Stop microphone monitoring
        stopMicrophoneMonitoring();

        // Update UI to show stopped state
        document.getElementById("record-btn").innerHTML =
            '<i class="fas fa-microphone me-2"></i>Record Answer';
        document.getElementById("record-btn").classList.remove("btn-warning");
        document.getElementById("record-btn").classList.add("btn-danger");
        document.getElementById("recording-indicator").style.display = "none";
    }
}

// Submit answer
async function submitAnswer() {
    try {
        const answer =
            recognizedText ||
            document.getElementById("transcribed-text").textContent;

        if (!answer.trim()) {
            showError("Please record an answer before submitting.");
            return;
        }

        // Show loading state on submit button
        const submitBtn = document.getElementById("submit-btn");
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML =
            '<i class="fas fa-spinner fa-spin me-2"></i>Traitement...';

        const response = await fetch("/api/submit_answer", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                question: currentQuestionText,
                answer: answer,
            }),
        });

        const data = await response.json();

        if (data.success) {
            if (data.completed) {
                showCompletionScreen();
            } else {
                currentQuestion = data.question_number;
                updateProgress();
                displayQuestion(data.next_question);
                await sendTextToHeygen(data.next_question);
                resetForNextQuestion();
            }
        } else {
            // Restore button state on error
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
            throw new Error(data.error || "Failed to submit answer");
        }
    } catch (error) {
        // Restore button state on error
        const submitBtn = document.getElementById("submit-btn");
        submitBtn.disabled = false;
        submitBtn.innerHTML =
            '<i class="fas fa-paper-plane me-2"></i>Soumettre Réponse';
        console.error("Error submitting answer:", error);
        showError("Failed to submit answer. Please try again.");
    }
}

// Update progress
function updateProgress() {
    for (let i = 1; i <= 8; i++) {
        const step = document.getElementById(`step${i}`);
        if (i < currentQuestion) {
            step.classList.add("completed");
            step.classList.remove("active");
        } else if (i === currentQuestion) {
            step.classList.add("active");
            step.classList.remove("completed");
        } else {
            step.classList.remove("active", "completed");
        }
    }

    document.getElementById("current-question").textContent = currentQuestion;
}

// Reset for next question
function resetForNextQuestion() {
    document.getElementById("answer-section").style.display = "none";
    document.getElementById("submit-btn").style.display = "none";
    document.getElementById("transcribed-text").textContent = "";
    recognizedText = "";

    // Reset submit button state
    const submitBtn = document.getElementById("submit-btn");
    submitBtn.disabled = false;
    submitBtn.innerHTML =
        '<i class="fas fa-paper-plane me-2"></i>Soumettre Réponse';

    // Reset speech recognition state
    resetSpeechRecognition();
}

// Completion screen
function showCompletionScreen() {
    document.getElementById("assessment-interface").style.display = "none";
    document.getElementById("completion-screen").style.display = "block";

    for (let i = 1; i <= 5; i++) {
        document.getElementById(`step${i}`).classList.add("completed");
        document.getElementById(`step${i}`).classList.remove("active");
    }
}

// Generate report
async function generateReport() {
    try {
        const button = document.getElementById("generate-report-btn");
        button.disabled = true;
        button.innerHTML =
            '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';

        const response = await fetch("/api/generate_report", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        });

        const data = await response.json();

        if (data.success) {
            await closeHeygenSession();
            window.location.href = "/report";
        } else {
            throw new Error(data.error || "Failed to generate report");
        }
    } catch (error) {
        console.error("Error generating report:", error);
        showError("Failed to generate report. Please try again.");

        const button = document.getElementById("generate-report-btn");
        button.disabled = false;
        button.innerHTML =
            '<i class="fas fa-file-pdf me-2"></i>Generate Report';
    }
}

// Error message
function showError(message) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "alert alert-danger alert-dismissible fade show";
    errorDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const container = document.querySelector(".container");
    container.insertBefore(errorDiv, container.firstChild);

    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

// Reset speech recognition state
function resetSpeechRecognition() {
    if (speechRecognition && isRecording) {
        try {
            speechRecognition.abort();
        } catch (error) {
            console.error("Error aborting speech recognition:", error);
        }
    }
    isRecording = false;
    speechRecognition = null;

    // Stop microphone monitoring
    stopMicrophoneMonitoring();

    // Reset UI
    document.getElementById("record-btn").innerHTML =
        '<i class="fas fa-microphone me-2"></i>Record Answer';
    document.getElementById("record-btn").classList.remove("btn-warning");
    document.getElementById("record-btn").classList.add("btn-danger");
    document.getElementById("recording-indicator").style.display = "none";
}

// Request microphone permissions
async function requestMicrophonePermission() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: true,
        });
        // Close the stream immediately as we only needed to request permission
        stream.getTracks().forEach((track) => track.stop());
        return true;
    } catch (error) {
        console.error("Microphone permission denied:", error);
        showError(
            "Microphone access is required for voice recognition. Please allow microphone access and refresh the page.",
        );
        return false;
    }
}

// Test speech recognition functionality
async function testSpeechRecognition() {
    try {
        if (!BrowserSpeechRecognition.isSupported()) {
            console.log("Speech recognition not supported");
            return false;
        }

        // Test microphone first
        console.log("Testing microphone...");
        const micWorking = await testMicrophone();
        if (!micWorking) {
            console.log("Microphone not working properly");
            showError(
                "Microphone is not working properly. Please check your microphone and permissions.",
            );
            return false;
        }
        console.log("Microphone test passed");

        // Try to create a simple instance to test
        const testRecognition = new BrowserSpeechRecognition();
        testRecognition.initialize();
        console.log("Speech recognition test passed");
        return true;
    } catch (error) {
        console.error("Speech recognition test failed:", error);
        return false;
    }
}

// Test microphone functionality
async function testMicrophone() {
    try {
        console.log("Testing microphone...");
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: true,
        });

        // Test if we can get audio levels
        const audioContext = new (window.AudioContext ||
            window.webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        const microphone = audioContext.createMediaStreamSource(stream);
        microphone.connect(analyser);

        analyser.fftSize = 256;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        return new Promise((resolve) => {
            let testDuration = 0;
            const maxTestTime = 2000; // 2 seconds

            function checkAudio() {
                analyser.getByteFrequencyData(dataArray);
                const average =
                    dataArray.reduce((sum, value) => sum + value, 0) /
                    dataArray.length;

                console.log("Microphone level:", average);

                if (average > 0 || testDuration >= maxTestTime) {
                    stream.getTracks().forEach((track) => track.stop());
                    microphone.disconnect();
                    resolve(average > 0);
                } else {
                    testDuration += 100;
                    setTimeout(checkAudio, 100);
                }
            }

            checkAudio();
        });
    } catch (error) {
        console.error("Microphone test failed:", error);
        return false;
    }
}

// Add microphone level monitoring
let audioContext = null;
let analyser = null;
let microphone = null;
let isMonitoringAudio = false;

async function startMicrophoneMonitoring() {
    try {
        if (!audioContext) {
            audioContext = new (window.AudioContext ||
                window.webkitAudioContext)();
        }

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: true,
        });
        microphone = audioContext.createMediaStreamSource(stream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;

        microphone.connect(analyser);

        isMonitoringAudio = true;
        monitorAudioLevel();

        return stream;
    } catch (error) {
        console.error("Failed to start microphone monitoring:", error);
        return null;
    }
}

function monitorAudioLevel() {
    if (!isMonitoringAudio || !analyser) return;

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(dataArray);

    // Calculate average volume
    const average =
        dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;

    // Update visual indicator based on audio level
    const indicator = document.getElementById("recording-indicator");
    if (indicator && isRecording) {
        if (average > 10) {
            indicator.style.color = "#28a745"; // Green when audio detected
            indicator.style.opacity = Math.min(1, average / 50);
        } else {
            indicator.style.color = "#dc3545"; // Red when no audio
            indicator.style.opacity = 0.5;
        }
    }

    // Continue monitoring
    if (isMonitoringAudio) {
        requestAnimationFrame(monitorAudioLevel);
    }
}

function stopMicrophoneMonitoring() {
    isMonitoringAudio = false;
    if (microphone) {
        microphone.disconnect();
        microphone = null;
    }
    if (analyser) {
        analyser = null;
    }
}

// Event listeners
document.addEventListener("DOMContentLoaded", function () {
    document
        .getElementById("play-question-btn")
        .addEventListener("click", playQuestion);
    document
        .getElementById("record-btn")
        .addEventListener("click", function () {
            if (isRecording) {
                stopVoiceRecognition();
            } else {
                startVoiceRecognition();
            }
        });
    document
        .getElementById("submit-btn")
        .addEventListener("click", submitAnswer);
    document
        .getElementById("generate-report-btn")
        .addEventListener("click", generateReport);
});
