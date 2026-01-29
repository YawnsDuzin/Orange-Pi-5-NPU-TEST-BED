/**
 * ROI Canvas - Interactive Region of Interest Drawing
 *
 * Supports rectangle, polygon, and line ROI types.
 * Handles both mouse and touch input.
 * Outputs normalized coordinates (0.0 - 1.0).
 */
class ROICanvas {
    constructor(canvasId, options = {}) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;

        this.ctx = this.canvas.getContext('2d');
        this.tool = 'rectangle'; // 'rectangle', 'polygon', 'line'
        this.rois = [];
        this.currentPoints = [];
        this.isDrawing = false;
        this.dragStart = null;

        // Options
        this.strokeColor = options.strokeColor || '#00ff00';
        this.fillColor = options.fillColor || 'rgba(0, 255, 0, 0.15)';
        this.lineWidth = options.lineWidth || 2;
        this.pointRadius = options.pointRadius || 5;

        // Callbacks
        this.onROICreated = options.onROICreated || null;
        this.onROIDeleted = options.onROIDeleted || null;

        this._setupEventListeners();
        this._resizeCanvas();

        window.addEventListener('resize', () => this._resizeCanvas());
    }

    setTool(tool) {
        this.tool = tool;
        this.currentPoints = [];
        this.isDrawing = false;
        this.canvas.style.pointerEvents = 'auto';
        this.canvas.style.cursor = tool === 'polygon' ? 'crosshair' : 'crosshair';
    }

    clear() {
        this.rois = [];
        this.currentPoints = [];
        this.isDrawing = false;
        this._redraw();
    }

    addROI(roi) {
        this.rois.push(roi);
        this._redraw();
    }

    getROIs() {
        return this.rois.map(roi => ({
            ...roi,
            points: roi.points.map(p => ({
                x: p.x / this.canvas.width,
                y: p.y / this.canvas.height,
            })),
        }));
    }

    getNormalizedROIs() {
        return this.getROIs();
    }

    // --- Private Methods ---

    _setupEventListeners() {
        // Mouse events
        this.canvas.addEventListener('mousedown', (e) => this._onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this._onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this._onMouseUp(e));
        this.canvas.addEventListener('dblclick', (e) => this._onDoubleClick(e));

        // Touch events
        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this._onMouseDown(this._touchToMouse(touch));
        });
        this.canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this._onMouseMove(this._touchToMouse(touch));
        });
        this.canvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            this._onMouseUp({});
        });

        // Keyboard
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.currentPoints = [];
                this.isDrawing = false;
                this._redraw();
            }
            if (e.key === 'z' && e.ctrlKey) {
                this._undo();
            }
        });
    }

    _touchToMouse(touch) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            offsetX: touch.clientX - rect.left,
            offsetY: touch.clientY - rect.top,
        };
    }

    _resizeCanvas() {
        const parent = this.canvas.parentElement;
        if (parent) {
            this.canvas.width = parent.offsetWidth;
            this.canvas.height = parent.offsetHeight;
            this._redraw();
        }
    }

    _getPos(e) {
        return { x: e.offsetX, y: e.offsetY };
    }

    _onMouseDown(e) {
        const pos = this._getPos(e);

        if (this.tool === 'rectangle') {
            this.isDrawing = true;
            this.dragStart = pos;
            this.currentPoints = [pos];
        } else if (this.tool === 'polygon') {
            if (!this.isDrawing) {
                this.isDrawing = true;
                this.currentPoints = [pos];
            } else {
                this.currentPoints.push(pos);
            }
            this._redraw();
        } else if (this.tool === 'line') {
            if (!this.isDrawing) {
                this.isDrawing = true;
                this.currentPoints = [pos];
            } else {
                this.currentPoints.push(pos);
                this._finishROI();
            }
            this._redraw();
        }
    }

    _onMouseMove(e) {
        if (!this.isDrawing) return;
        const pos = this._getPos(e);

        if (this.tool === 'rectangle' && this.dragStart) {
            this._redraw();
            this._drawRectPreview(this.dragStart, pos);
        } else if (this.tool === 'polygon' && this.currentPoints.length > 0) {
            this._redraw();
            this._drawPolygonPreview(pos);
        } else if (this.tool === 'line' && this.currentPoints.length === 1) {
            this._redraw();
            this._drawLinePreview(this.currentPoints[0], pos);
        }
    }

    _onMouseUp(e) {
        if (this.tool === 'rectangle' && this.isDrawing) {
            const pos = this._getPos(e);
            if (this.dragStart) {
                const x1 = Math.min(this.dragStart.x, pos.x);
                const y1 = Math.min(this.dragStart.y, pos.y);
                const x2 = Math.max(this.dragStart.x, pos.x);
                const y2 = Math.max(this.dragStart.y, pos.y);

                if (Math.abs(x2 - x1) > 10 && Math.abs(y2 - y1) > 10) {
                    this.currentPoints = [
                        { x: x1, y: y1 },
                        { x: x2, y: y2 },
                    ];
                    this._finishROI();
                }
            }
            this.isDrawing = false;
            this.dragStart = null;
        }
    }

    _onDoubleClick(e) {
        if (this.tool === 'polygon' && this.currentPoints.length >= 3) {
            this._finishROI();
        }
    }

    _finishROI() {
        if (this.currentPoints.length < 2) return;

        const roi = {
            id: 'roi_' + Date.now(),
            type: this.tool,
            points: [...this.currentPoints],
            color: this.strokeColor,
        };

        this.rois.push(roi);
        this.currentPoints = [];
        this.isDrawing = false;
        this._redraw();

        if (this.onROICreated) {
            const normalized = {
                ...roi,
                points: roi.points.map(p => ({
                    x: p.x / this.canvas.width,
                    y: p.y / this.canvas.height,
                })),
            };
            this.onROICreated(normalized);
        }
    }

    _undo() {
        if (this.currentPoints.length > 0) {
            this.currentPoints.pop();
            if (this.currentPoints.length === 0) {
                this.isDrawing = false;
            }
        } else if (this.rois.length > 0) {
            const removed = this.rois.pop();
            if (this.onROIDeleted) {
                this.onROIDeleted(removed);
            }
        }
        this._redraw();
    }

    _redraw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw existing ROIs
        for (const roi of this.rois) {
            this._drawROI(roi);
        }

        // Draw current points
        if (this.currentPoints.length > 0 && this.tool === 'polygon') {
            this.ctx.beginPath();
            this.ctx.setLineDash([5, 5]);
            this.ctx.strokeStyle = this.strokeColor;
            this.ctx.lineWidth = this.lineWidth;
            this.ctx.moveTo(this.currentPoints[0].x, this.currentPoints[0].y);
            for (let i = 1; i < this.currentPoints.length; i++) {
                this.ctx.lineTo(this.currentPoints[i].x, this.currentPoints[i].y);
            }
            this.ctx.stroke();
            this.ctx.setLineDash([]);

            // Draw points
            for (const p of this.currentPoints) {
                this.ctx.beginPath();
                this.ctx.arc(p.x, p.y, this.pointRadius, 0, Math.PI * 2);
                this.ctx.fillStyle = this.strokeColor;
                this.ctx.fill();
            }
        }
    }

    _drawROI(roi) {
        const ctx = this.ctx;
        ctx.strokeStyle = roi.color || this.strokeColor;
        ctx.lineWidth = this.lineWidth;

        if (roi.type === 'rectangle' && roi.points.length === 2) {
            const [p1, p2] = roi.points;
            const w = p2.x - p1.x;
            const h = p2.y - p1.y;

            ctx.fillStyle = this.fillColor;
            ctx.fillRect(p1.x, p1.y, w, h);
            ctx.strokeRect(p1.x, p1.y, w, h);
        } else if (roi.type === 'line' && roi.points.length === 2) {
            ctx.beginPath();
            ctx.moveTo(roi.points[0].x, roi.points[0].y);
            ctx.lineTo(roi.points[1].x, roi.points[1].y);
            ctx.stroke();

            // Draw endpoints
            for (const p of roi.points) {
                ctx.beginPath();
                ctx.arc(p.x, p.y, this.pointRadius, 0, Math.PI * 2);
                ctx.fillStyle = roi.color || this.strokeColor;
                ctx.fill();
            }
        } else if (roi.type === 'polygon' && roi.points.length >= 3) {
            ctx.beginPath();
            ctx.moveTo(roi.points[0].x, roi.points[0].y);
            for (let i = 1; i < roi.points.length; i++) {
                ctx.lineTo(roi.points[i].x, roi.points[i].y);
            }
            ctx.closePath();
            ctx.fillStyle = this.fillColor;
            ctx.fill();
            ctx.stroke();
        }
    }

    _drawRectPreview(start, end) {
        const ctx = this.ctx;
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = this.strokeColor;
        ctx.lineWidth = this.lineWidth;
        ctx.strokeRect(start.x, start.y, end.x - start.x, end.y - start.y);
        ctx.setLineDash([]);
    }

    _drawPolygonPreview(currentPos) {
        if (this.currentPoints.length === 0) return;
        const ctx = this.ctx;
        const lastPoint = this.currentPoints[this.currentPoints.length - 1];
        ctx.beginPath();
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = this.strokeColor;
        ctx.lineWidth = 1;
        ctx.moveTo(lastPoint.x, lastPoint.y);
        ctx.lineTo(currentPos.x, currentPos.y);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    _drawLinePreview(start, end) {
        const ctx = this.ctx;
        ctx.beginPath();
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = this.strokeColor;
        ctx.lineWidth = this.lineWidth;
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
        ctx.setLineDash([]);
    }
}

// Global instance
window.ROICanvas = ROICanvas;
