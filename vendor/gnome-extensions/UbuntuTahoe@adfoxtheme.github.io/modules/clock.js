import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export class TahoeClockManager {
    constructor() {
        this._dateMenu = null;
        this._originalBox = null;
        this._originalIndex = -1;
        this._panelBoxes = null;
        this._signals = [];
        this._repositioning = false;
        this._currentBoxIndex = -1;
        this._currentOffset = 0;
    }

    enable(targetBoxIndex = 0, targetOffset = 0) {
        if (targetBoxIndex < 0) {
            return;
        }

        this._dateMenu = Main.panel.statusArea.dateMenu;
        if (!this._dateMenu) return;

        this._panelBoxes = [
            Main.panel._centerBox, // 0: Center (GNOME default)
            Main.panel._rightBox,  // 1: Right (macOS style)
            Main.panel._leftBox,   // 2: Left
        ];

        this._currentBoxIndex = targetBoxIndex;
        this._currentOffset = targetOffset;
        this._applyPosition(targetBoxIndex, targetOffset);

        // Keep clock in desired position if other items are added/reordered
        this._signals = this._panelBoxes.map(box => {
            return box.connect('child-added', () => {
                if (!this._repositioning && this._currentBoxIndex >= 0) {
                    this._applyPosition(this._currentBoxIndex, this._currentOffset);
                }
            });
        });
    }

    reposition(targetBoxIndex = 0, targetOffset = 0) {
        if (targetBoxIndex < 0) {
            this.disable();
            return;
        }

        if (!this._dateMenu) {
            this.enable(targetBoxIndex, targetOffset);
            return;
        }

        this._currentBoxIndex = targetBoxIndex;
        this._currentOffset = targetOffset;
        this._applyPosition(targetBoxIndex, targetOffset);
    }

    _applyPosition(targetBoxIndex, targetOffset) {
        if (!this._dateMenu || !this._panelBoxes) return;

        const container = this._dateMenu.container;
        if (!container) return;

        let fromBoxIndex = -1;
        let fromIndex = -1;

        for (let i = 0; i < 3; i++) {
            const idx = this._panelBoxes[i].get_children().indexOf(container);
            if (idx !== -1) {
                fromBoxIndex = i;
                fromIndex = idx;
                break;
            }
        }

        if (fromBoxIndex === -1) return;

        // Remember original placement
        if (this._originalBox === null) {
            this._originalBox = this._panelBoxes[fromBoxIndex];
            this._originalIndex = fromIndex;
        }

        const targetBox = this._panelBoxes[targetBoxIndex];
        const children = targetBox.get_children();
        const destIndex = Math.min(targetOffset, children.length);

        if (fromBoxIndex === targetBoxIndex && fromIndex === destIndex) {
            return;
        }

        this._repositioning = true;
        try {
            this._panelBoxes[fromBoxIndex].remove_child(container);
            targetBox.insert_child_at_index(container, destIndex);
        } finally {
            this._repositioning = false;
        }
    }

    disable() {
        if (this._signals.length > 0 && this._panelBoxes) {
            this._panelBoxes.forEach((box, i) => {
                if (this._signals[i]) {
                    box.disconnect(this._signals[i]);
                }
            });
            this._signals = [];
        }

        if (this._dateMenu && this._originalBox) {
            const container = this._dateMenu.container;
            if (container) {
                for (let i = 0; i < 3; i++) {
                    if (this._panelBoxes && this._panelBoxes[i].get_children().includes(container)) {
                        this._panelBoxes[i].remove_child(container);
                        break;
                    }
                }
                const maxIdx = this._originalBox.get_children().length;
                const returnIdx = Math.min(this._originalIndex >= 0 ? this._originalIndex : 0, maxIdx);
                this._originalBox.insert_child_at_index(container, returnIdx);
            }
        }

        this._dateMenu = null;
        this._originalBox = null;
        this._panelBoxes = null;
        this._currentBoxIndex = -1;
    }
}

export class TahoeActivitiesManager {
    constructor() {
        this._activities = null;
    }

    enable() {
        this._activities = Main.panel.statusArea.activities;
        if (this._activities?.container) {
            this._activities.container.hide();
        }
    }

    disable() {
        if (this._activities?.container) {
            this._activities.container.show();
        }
        this._activities = null;
    }
}
