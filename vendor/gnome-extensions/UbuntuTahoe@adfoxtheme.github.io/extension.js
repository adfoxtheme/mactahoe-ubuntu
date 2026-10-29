import Gio from 'gi://Gio';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

import { TahoeClockManager, TahoeActivitiesManager } from './modules/clock.js';
import { TahoeGlobalMenuManager } from './modules/globalmenu/manager.js';
import { TahoeKimpanelManager } from './modules/kimpanel/manager.js';
import { TahoeBlurManager } from './modules/blur/manager.js';

export default class UbuntuTahoeExtension extends Extension {
    constructor(metadata) {
        super(metadata);
        this._clockManager = null;
        this._activitiesManager = null;
        this._globalMenuManager = null;
        this._kimpanelManager = null;
        this._blurManager = null;
        this._suiteSettings = null;
        this._settingsChangedIds = [];
    }

    _getSchemaSettings(schemaId) {
        try {
            return this.getSettings(schemaId);
        } catch (e) {
            try {
                const schemaDir = this.dir.get_child('schemas').get_path();
                const source = Gio.SettingsSchemaSource.new_from_directory(
                    schemaDir,
                    Gio.SettingsSchemaSource.get_default(),
                    false
                );
                const schema = source.lookup(schemaId, true);
                if (schema) {
                    return new Gio.Settings({ settings_schema: schema });
                }
            } catch (err) {
                console.warn(`[UbuntuTahoe] Custom schema lookup error for ${schemaId}:`, err);
            }
            return new Gio.Settings({ schema_id: schemaId });
        }
    }

    enable() {
        console.log('[UbuntuTahoe] Enabling macOS Tahoe suite...');
        this._suiteSettings = this.getSettings();

        // 1. Clock Position
        this._updateClock();

        // 2. Activities Button
        this._updateActivities();

        // 3. Global Menu
        this._updateGlobalMenu();

        // 4. Input Method Panel (Kimpanel)
        this._updateKimpanel();

        // 5. Blur
        this._updateBlur();

        // Listen for live setting changes
        this._settingsChangedIds = [
            this._suiteSettings.connect('changed::clock-position', () => this._updateClock()),
            this._suiteSettings.connect('changed::clock-offset', () => this._updateClock()),
            this._suiteSettings.connect('changed::hide-activities', () => this._updateActivities()),
            this._suiteSettings.connect('changed::enable-globalmenu', () => this._updateGlobalMenu()),
            this._suiteSettings.connect('changed::enable-kimpanel', () => this._updateKimpanel()),
            this._suiteSettings.connect('changed::enable-blur', () => this._updateBlur()),
        ];

        console.log('[UbuntuTahoe] macOS Tahoe suite enabled successfully.');
    }

    _updateClock() {
        try {
            const pos = this._suiteSettings.get_int('clock-position');
            const offset = this._suiteSettings.get_int('clock-offset');
            if (pos < 0) {
                if (this._clockManager) {
                    this._clockManager.disable();
                    this._clockManager = null;
                }
                return;
            }
            if (!this._clockManager) {
                this._clockManager = new TahoeClockManager();
                this._clockManager.enable(pos, offset);
            } else {
                this._clockManager.reposition(pos, offset);
            }
        } catch (err) {
            console.error('[UbuntuTahoe] Failed to update clock position:', err);
        }
    }

    _updateActivities() {
        try {
            const hide = this._suiteSettings.get_boolean('hide-activities');
            if (hide) {
                if (!this._activitiesManager) {
                    this._activitiesManager = new TahoeActivitiesManager();
                    this._activitiesManager.enable();
                }
            } else if (this._activitiesManager) {
                this._activitiesManager.disable();
                this._activitiesManager = null;
            }
        } catch (err) {
            console.error('[UbuntuTahoe] Failed to update activities button:', err);
        }
    }

    _updateGlobalMenu() {
        try {
            const enable = this._suiteSettings.get_boolean('enable-globalmenu');
            if (enable) {
                if (!this._globalMenuManager) {
                    const globalMenuSettings = this._getSchemaSettings('org.gnome.shell.extensions.globalmenu');
                    this._globalMenuManager = new TahoeGlobalMenuManager(
                        this.path,
                        globalMenuSettings,
                        this.metadata.uuid
                    );
                    this._globalMenuManager.enable();
                }
            } else if (this._globalMenuManager) {
                this._globalMenuManager.disable();
                this._globalMenuManager = null;
            }
        } catch (err) {
            console.error('[UbuntuTahoe] Failed to update Global Menu:', err);
        }
    }

    _updateKimpanel() {
        try {
            const enable = this._suiteSettings.get_boolean('enable-kimpanel');
            if (enable) {
                if (!this._kimpanelManager) {
                    const kimSettings = this._getSchemaSettings('org.gnome.shell.extensions.kimpanel');
                    this._kimpanelManager = new TahoeKimpanelManager(kimSettings);
                    this._kimpanelManager.enable();
                }
            } else if (this._kimpanelManager) {
                this._kimpanelManager.disable();
                this._kimpanelManager = null;
            }
        } catch (err) {
            console.error('[UbuntuTahoe] Failed to update Kimpanel:', err);
        }
    }

    _updateBlur() {
        try {
            const enable = this._suiteSettings.get_boolean('enable-blur');
            if (enable) {
                if (!this._blurManager) {
                    const blurSettings = this._getSchemaSettings('org.gnome.shell.extensions.blur-my-shell');
                    this._blurManager = new TahoeBlurManager(blurSettings);
                    this._blurManager.enable();
                }
            } else if (this._blurManager) {
                this._blurManager.disable();
                this._blurManager = null;
            }
        } catch (err) {
            console.error('[UbuntuTahoe] Failed to update Blur:', err);
        }
    }

    disable() {
        console.log('[UbuntuTahoe] Disabling macOS Tahoe suite...');

        if (this._settingsChangedIds && this._suiteSettings) {
            this._settingsChangedIds.forEach(id => this._suiteSettings.disconnect(id));
            this._settingsChangedIds = [];
        }

        if (this._blurManager) {
            try { this._blurManager.disable(); } catch (err) { console.error('[UbuntuTahoe] Error disabling blur:', err); }
            this._blurManager = null;
        }

        if (this._kimpanelManager) {
            try { this._kimpanelManager.disable(); } catch (err) { console.error('[UbuntuTahoe] Error disabling kimpanel:', err); }
            this._kimpanelManager = null;
        }

        if (this._globalMenuManager) {
            try { this._globalMenuManager.disable(); } catch (err) { console.error('[UbuntuTahoe] Error disabling global menu:', err); }
            this._globalMenuManager = null;
        }

        if (this._activitiesManager) {
            try { this._activitiesManager.disable(); } catch (err) { console.error('[UbuntuTahoe] Error restoring activities:', err); }
            this._activitiesManager = null;
        }

        if (this._clockManager) {
            try { this._clockManager.disable(); } catch (err) { console.error('[UbuntuTahoe] Error restoring clock position:', err); }
            this._clockManager = null;
        }

        this._suiteSettings = null;
        console.log('[UbuntuTahoe] macOS Tahoe suite disabled successfully.');
    }
}
