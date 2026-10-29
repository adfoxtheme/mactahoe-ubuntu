import GLib from 'gi://GLib';

class PointerWatch {
    constructor(watcher, interval, callback) {
        this.watcher = watcher;
        this.interval = interval;
        this.callback = callback;
    }

    remove() {
        this.watcher._removeWatch(this);
    }
}

let _pointerWatcher = null;

export class PointerWatcher {
    constructor() {
        this._idleId = 0;
        this._watches = [];
    }

    _getPointer() {
        try {
            if (global.backend && typeof global.backend.get_cursor_tracker === 'function') {
                const res = global.backend.get_cursor_tracker().get_pointer();
                if (res && res[0]) {
                    const c = res[0];
                    if (typeof c.x === 'number' && typeof c.y === 'number') {
                        return [c.x, c.y];
                    }
                    if (typeof c === 'number' && typeof res[1] === 'number') {
                        return [c, res[1]];
                    }
                }
            }
        } catch (_) {}
        try {
            if (typeof global.get_pointer === 'function') {
                const [x, y] = global.get_pointer();
                if (typeof x === 'number' && typeof y === 'number') {
                    return [x, y];
                }
            }
        } catch (_) {}
        return [0, 0];
    }

    addWatch(interval, callback) {
        const watch = new PointerWatch(this, interval, callback);
        this._watches.push(watch);
        this._updateWatch();
        return watch;
    }

    _removeWatch(watch) {
        const index = this._watches.indexOf(watch);
        if (index !== -1)
            this._watches.splice(index, 1);
        this._updateWatch();
    }

    _updateWatch() {
        if (this._watches.length === 0) {
            if (this._idleId) {
                GLib.source_remove(this._idleId);
                this._idleId = 0;
            }
            return;
        }

        if (this._idleId)
            return;

        let interval = 100;
        for (const w of this._watches) {
            if (w.interval && w.interval < interval)
                interval = w.interval;
        }

        this._idleId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, interval, () => {
            const [x, y] = this._getPointer();
            for (const watch of [...this._watches]) {
                try {
                    watch.callback(x, y);
                } catch (e) {
                    console.error('[PointerWatcher] Error in watch callback:', e);
                }
            }
            return GLib.SOURCE_CONTINUE;
        });
    }
}

export function getPointerWatcher() {
    if (_pointerWatcher == null)
        _pointerWatcher = new PointerWatcher();
    return _pointerWatcher;
}
