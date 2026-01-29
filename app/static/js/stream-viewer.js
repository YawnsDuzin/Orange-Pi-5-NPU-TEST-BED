/**
 * Stream Viewer - WebSocket-based video stream handler
 *
 * Manages WebSocket connection to the server for receiving
 * video frames and inference metadata in real-time.
 */
class StreamViewer {
    constructor(options = {}) {
        this.imageElement = options.imageElement || null;
        this.canvasElement = options.canvasElement || null;
        this.metadataCallback = options.onMetadata || null;
        this.statusCallback = options.onStatusChange || null;

        this.ws = null;
        this.cameraId = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this._reconnectTimer = null;
    }

    /**
     * Connect to a camera's WebSocket stream.
     */
    connect(cameraId) {
        this.disconnect();
        this.cameraId = cameraId;
        this.reconnectAttempts = 0;
        this._connect();
    }

    /**
     * Disconnect from the stream.
     */
    disconnect() {
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.connected = false;
        this.cameraId = null;
        this._updateStatus('disconnected');
    }

    /**
     * Check if currently connected.
     */
    isConnected() {
        return this.connected && this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    // --- Private ---

    _connect() {
        if (!this.cameraId) return;

        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/api/stream/${this.cameraId}/ws`;

        this._updateStatus('connecting');

        try {
            this.ws = new WebSocket(url);
            this.ws.binaryType = 'arraybuffer';

            this.ws.onopen = () => {
                this.connected = true;
                this.reconnectAttempts = 0;
                this._updateStatus('connected');
            };

            this.ws.onmessage = (event) => {
                this._handleMessage(event);
            };

            this.ws.onclose = (event) => {
                this.connected = false;
                this._updateStatus('disconnected');

                // Auto-reconnect
                if (this.cameraId && this.reconnectAttempts < this.maxReconnectAttempts) {
                    const delay = Math.min(
                        this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts),
                        10000
                    );
                    this.reconnectAttempts++;
                    this._reconnectTimer = setTimeout(() => this._connect(), delay);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this._updateStatus('error');
            };

        } catch (e) {
            console.error('WebSocket connection failed:', e);
            this._updateStatus('error');
        }
    }

    _handleMessage(event) {
        try {
            const data = JSON.parse(event.data);

            if (data.type === 'frame') {
                // Display frame
                if (this.imageElement && data.image) {
                    this.imageElement.src = 'data:image/jpeg;base64,' + data.image;
                }

                // Forward metadata
                if (this.metadataCallback && data.inference) {
                    this.metadataCallback(data.inference);
                }

            } else if (data.type === 'heartbeat') {
                // Respond to heartbeat
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ type: 'ping' }));
                }
            }
        } catch (e) {
            console.error('Error handling message:', e);
        }
    }

    _updateStatus(status) {
        if (this.statusCallback) {
            this.statusCallback(status, this.cameraId);
        }
    }
}

// Global instance
window.StreamViewer = StreamViewer;
