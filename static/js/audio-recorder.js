// Audio recorder utility class
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
    }

    async initialize() {
        try {
            // Check for browser support
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Audio recording not supported in this browser');
            }

            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000
                }
            });

            return true;
        } catch (error) {
            console.error('Error initializing audio recorder:', error);
            throw error;
        }
    }

    async startRecording() {
        try {
            if (!this.stream) {
                await this.initialize();
            }

            this.audioChunks = [];
            
            // Create MediaRecorder with appropriate options
            const options = {
                mimeType: 'audio/webm;codecs=opus',
                audioBitsPerSecond: 16000
            };

            // Fallback MIME types for different browsers
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                if (MediaRecorder.isTypeSupported('audio/wav')) {
                    options.mimeType = 'audio/wav';
                } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
                    options.mimeType = 'audio/mp4';
                } else {
                    delete options.mimeType;
                }
            }

            this.mediaRecorder = new MediaRecorder(this.stream, options);

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.isRecording = false;
            };

            this.mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event.error);
                this.isRecording = false;
            };

            this.mediaRecorder.start(100); // Collect data every 100ms
            this.isRecording = true;

            return true;
        } catch (error) {
            console.error('Error starting recording:', error);
            throw error;
        }
    }

    stopRecording() {
        return new Promise((resolve) => {
            if (this.mediaRecorder && this.isRecording) {
                this.mediaRecorder.onstop = () => {
                    this.isRecording = false;
                    const audioBlob = new Blob(this.audioChunks, { 
                        type: this.mediaRecorder.mimeType || 'audio/wav' 
                    });
                    resolve(audioBlob);
                };
                
                this.mediaRecorder.stop();
            } else {
                resolve(null);
            }
        });
    }

    getAudioBlob() {
        if (this.audioChunks.length > 0) {
            return new Blob(this.audioChunks, { type: 'audio/wav' });
        }
        return null;
    }

    cleanup() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.mediaRecorder) {
            this.mediaRecorder = null;
        }
        
        this.audioChunks = [];
        this.isRecording = false;
    }

    // Static method to check browser support
    static isSupported() {
        return !!(navigator.mediaDevices && 
                  navigator.mediaDevices.getUserMedia && 
                  window.MediaRecorder);
    }

    // Get recording duration estimate
    getDurationEstimate() {
        // This is a rough estimate based on data chunks
        // In a real implementation, you'd want to use the Web Audio API
        return this.audioChunks.length * 0.1; // Assuming 100ms chunks
    }
}

// Audio player utility
class AudioPlayer {
    constructor() {
        this.audio = null;
        this.isPlaying = false;
    }

    async playFromUrl(url) {
        try {
            if (this.audio) {
                this.audio.pause();
                this.audio.currentTime = 0;
            }

            this.audio = new Audio(url);
            
            return new Promise((resolve, reject) => {
                this.audio.onloadeddata = () => {
                    this.audio.play()
                        .then(() => {
                            this.isPlaying = true;
                            resolve();
                        })
                        .catch(reject);
                };
                
                this.audio.onended = () => {
                    this.isPlaying = false;
                };
                
                this.audio.onerror = () => {
                    reject(new Error('Failed to load audio'));
                };
            });
        } catch (error) {
            console.error('Error playing audio:', error);
            throw error;
        }
    }

    async playFromBlob(blob) {
        try {
            const url = URL.createObjectURL(blob);
            await this.playFromUrl(url);
            // Clean up the object URL after playing
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch (error) {
            console.error('Error playing audio from blob:', error);
            throw error;
        }
    }

    stop() {
        if (this.audio) {
            this.audio.pause();
            this.audio.currentTime = 0;
            this.isPlaying = false;
        }
    }

    pause() {
        if (this.audio) {
            this.audio.pause();
            this.isPlaying = false;
        }
    }

    resume() {
        if (this.audio) {
            this.audio.play();
            this.isPlaying = true;
        }
    }
}

// Export for use in other files
window.AudioRecorder = AudioRecorder;
window.AudioPlayer = AudioPlayer;
