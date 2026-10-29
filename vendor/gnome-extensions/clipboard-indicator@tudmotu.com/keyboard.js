import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export class Keyboard {
    #device;
    #contentPurpose;

    constructor () {
        try {
            let seat = null;
            if (global.stage && global.stage.context) {
                seat = global.stage.context.get_backend().get_default_seat();
            } else if (typeof Clutter.get_default_backend === 'function') {
                seat = Clutter.get_default_backend().get_default_seat();
            } else if (global.backend && typeof global.backend.get_default_seat === 'function') {
                seat = global.backend.get_default_seat();
            }
            if (seat && typeof seat.create_virtual_device === 'function') {
                this.#device = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
            }
        } catch (e) {
            console.warn(`[clipboard-indicator] Could not create virtual keyboard device: ${e}`);
        }

        if (Main.inputMethod) {
            Main.inputMethod.connectObject('notify::content-purpose', (method) => {
                this.#contentPurpose = method.content_purpose;
            }, this);
        }
    }

    destroy () {
        if (Main.inputMethod) {
            Main.inputMethod.disconnectObject(this);
        }
        if (this.#device) {
            this.#device.run_dispose();
            this.#device = null;
        }
    }

    #notify (key, state) {
        if (!this.#device) return;
        try {
            this.#device.notify_keyval(
                Clutter.get_current_event_time() * 1000,
                key,
                state
            );
        } catch (e) {
            console.warn(`[clipboard-indicator] notify_keyval error: ${e}`);
        }
    }

    get purpose () {
        return this.#contentPurpose;
    }

    press (key) {
        this.#notify(key, Clutter.KeyState.PRESSED);
    }

    release (key) {
        this.#notify(key, Clutter.KeyState.RELEASED);
    }
}
