// Thay thế cho resource:///org/gnome/shell/ui/pointerWatcher.js (đã bị GNOME Shell 51 xóa).
// Giữ nguyên giao diện getPointerWatcher().addWatch(interval, callback) / _removeWatch(watch)
// mà docking.js đang dùng, nhưng đọc vị trí con trỏ qua Meta.CursorTracker.
import GLib from 'gi://GLib';

const MIN_INTERVAL_MS = 16;

function getPointerPosition() {
    try {
        // Tuỳ phiên bản mutter: trả về [x, y, mods] hoặc [Graphene.Point, mods].
        const result = global.backend.get_cursor_tracker().get_pointer();
        if (typeof result[0] === 'number')
            return [result[0], result[1]];
        return [result[0].x, result[0].y];
    } catch (e) {
        // GNOME Shell cũ hơn: global.get_pointer() vẫn còn.
        const [x, y] = global.get_pointer();
        return [x, y];
    }
}

class PointerWatch {
    constructor(interval, callback) {
        this._callback = callback;
        this._lastX = null;
        this._lastY = null;
        this._sourceId = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT, Math.max(interval, MIN_INTERVAL_MS), () => {
                const [x, y] = getPointerPosition();
                if (x !== this._lastX || y !== this._lastY) {
                    this._lastX = x;
                    this._lastY = y;
                    this._callback(x, y);
                }
                return GLib.SOURCE_CONTINUE;
            });
        GLib.Source.set_name_by_id(this._sourceId, '[UbuntuTahoeDock] pointer watch');
    }

    remove() {
        if (this._sourceId) {
            GLib.source_remove(this._sourceId);
            this._sourceId = 0;
        }
    }
}

class PointerWatcher {
    addWatch(interval, callback) {
        return new PointerWatch(interval, callback);
    }

    _removeWatch(watch) {
        watch?.remove();
    }
}

const watcher = new PointerWatcher();

export function getPointerWatcher() {
    return watcher;
}
