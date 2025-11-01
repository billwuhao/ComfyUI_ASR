/**
 * MW COLOR Widget for ComfyUI
 * A simplified color picker that outputs a hex color string.
 * Based on the original Color Widget by AILab.
 */

import { app } from "/scripts/app.js";

const MWColorWidget = {
    COLORHEX: (key, val) => {
        const widget = {};
        widget.y = 0;
        widget.name = key;
        widget.type = 'COLORHEX';
        
        const defaultValue = '#f30e0eff';
        widget.value = typeof val === 'string' ? val : defaultValue;

        widget.draw = function (ctx, node, widgetWidth, widgetY, height) {
            const margin = 15;
            const radius = 12;

            ctx.fillStyle = this.value;
            
            ctx.beginPath();
            const x = margin;
            const y = widgetY;
            const w = widgetWidth - margin * 2;
            const h = height;

            ctx.moveTo(x + radius, y);
            ctx.lineTo(x + w - radius, y);
            ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
            ctx.lineTo(x + w, y + h - radius);
            ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
            ctx.lineTo(x + radius, y + h);
            ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
            ctx.lineTo(x, y + radius);
            ctx.quadraticCurveTo(x, y, x + radius, y);
            ctx.closePath();
            ctx.fill();

            ctx.strokeStyle = '#555';
            ctx.lineWidth = 1;
            ctx.stroke();
        };

        widget.mouse = function (e, pos, node) {
            if (e.type === 'pointerdown') {
                const margin = 15;
                if (pos[0] >= margin && pos[0] <= node.size[0] - margin) {
                    const picker = document.createElement('input');
                    picker.type = 'color';
                    picker.value = this.value;

                    picker.style.position = 'absolute';
                    picker.style.left = '-9999px';
                    picker.style.top = '-9999px';

                    document.body.appendChild(picker);

                    picker.addEventListener('change', () => {
                        this.value = picker.value;
                        node.graph._version++;
                        node.setDirtyCanvas(true, true);
                        picker.remove();
                    });

                    picker.click();
                    return true;
                }
            }
            return false;
        };

        widget.computeSize = function (width) {
            return [width, 32];
        };

        return widget;
    }
};

app.registerExtension({
    name: "MW.colorWidget",

    getCustomWidgets() {
        return {
            COLORHEX: (node, inputName, inputData) => {
                return {
                    widget: node.addCustomWidget(
                        MWColorWidget.COLORHEX(inputName, inputData?.[1]?.default || '#f30e0eff')
                    ),
                    minWidth: 150,
                    minHeight: 32,
                };
            }
        };
    }
});