// SPDX-License-Identifier: GPL-3.0-or-later
// UbuntuTahoeSpotlight - macOS Tahoe Style Spotlight Search for GNOME 45-51

import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';
import * as AnimationUtils from 'resource:///org/gnome/shell/misc/animationUtils.js';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

function removeVietnameseDiacritics(str) {
    if (!str) return '';
    return str
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/đ/g, 'd')
        .replace(/Đ/g, 'D')
        .toLowerCase();
}

function shouldShowApp(app) {
    if (!app) return false;
    try {
        const info = app.app_info || (typeof app.get_app_info === 'function' ? app.get_app_info() : null);
        if (info && typeof info.should_show === 'function') {
            return info.should_show();
        }
    } catch (e) {}
    return true;
}

function scrollActorIntoView(scrollView, actor) {
    if (!scrollView || !actor) return;
    try {
        if (typeof AnimationUtils?.ensureActorVisibleInScrollView === 'function') {
            AnimationUtils.ensureActorVisibleInScrollView(scrollView, actor);
            return;
        }
    } catch (e) {}

    try {
        const vadj = scrollView.vadjustment;
        if (vadj) {
            const [, y] = actor.get_transformed_position();
            const [, scrollY] = scrollView.get_transformed_position();
            const top = y - scrollY;
            const bottom = top + actor.height;
            if (top < 0) {
                vadj.value += top;
            } else if (bottom > scrollView.height) {
                vadj.value += (bottom - scrollView.height);
            }
        }
    } catch (e) {}
}

const SpotlightDialog = GObject.registerClass(
class SpotlightDialog extends ModalDialog.ModalDialog {
    static {
        try {
            const pool = this.get_binding_pool();
            pool.install_closure(
                'close',
                Clutter.KEY_Escape,
                Clutter.RELEASE_MASK,
                obj => {
                    obj.close();
                    return Clutter.EVENT_STOP;
                }
            );
        } catch (e) {}
    }

    _init(extension) {
        super._init({
            styleClass: 'tahoe-spotlight-modal',
            destroyOnClose: false,
        });

        this._extension = extension;
        this._settings = extension.getSettings();
        this._selectedIndex = 0;
        this._results = [];
        this._itemWidgets = [];
        this._lastQuery = '';
        this._debounceTimerId = 0;
        this._indexedApps = null;

        // Centering on screen
        this.dialogLayout.x_align = Clutter.ActorAlign.CENTER;
        this.dialogLayout.y_align = Clutter.ActorAlign.CENTER;
        if (this.dialogLayout._dialog) {
            this.dialogLayout._dialog.x_align = Clutter.ActorAlign.CENTER;
            this.dialogLayout._dialog.y_align = Clutter.ActorAlign.CENTER;
            this.dialogLayout._dialog.margin_top = 0;
            this.dialogLayout._dialog.margin_bottom = 0;
        }
        this.buttonLayout.hide();

        // Dialog-level Escape key controller
        const dialogKeyController = new Clutter.KeyController();
        dialogKeyController.connect('key-press', () => {
            const [, symbol] = dialogKeyController.get_key();
            if (symbol === Clutter.KEY_Escape) {
                this.close();
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
        this.add_action(dialogKeyController);

        // Dismiss when clicking outside modal window
        if (this._eventBlocker) {
            this._eventBlocker.connect('button-press-event', () => {
                this.close();
                return Clutter.EVENT_STOP;
            });
        }

        this._buildUI();
    }

    _buildUI() {
        this.contentLayout.style_class = 'tahoe-spotlight-content';

        const mainContainer = new St.BoxLayout({
            orientation: Clutter.Orientation.VERTICAL,
            style_class: 'tahoe-spotlight-container',
        });

        // 1. Search Box Header
        const searchBox = new St.BoxLayout({
            orientation: Clutter.Orientation.HORIZONTAL,
            style_class: 'tahoe-spotlight-search-box',
            y_align: Clutter.ActorAlign.CENTER,
        });

        const searchIcon = new St.Icon({
            icon_name: 'system-search-symbolic',
            style_class: 'tahoe-spotlight-search-icon',
        });
        searchBox.add_child(searchIcon);

        this._entry = new St.Entry({
            style_class: 'tahoe-spotlight-entry',
            hint_text: 'Tìm kiếm ứng dụng, tính toán nhanh...',
            can_focus: true,
            x_expand: true,
        });

        // Live debounced search (smooth 60ms debounce, supports Fcitx5 preedit)
        this._entry.clutter_text.connect('text-changed', () => this._scheduleSearch());
        this._entry.clutter_text.connect('cursor-changed', () => this._scheduleSearch());
        this._entry.clutter_text.connect('key-release-event', () => {
            this._scheduleSearch();
            return Clutter.EVENT_PROPAGATE;
        });

        // Handle Return / Enter activation directly from entry text
        this._entry.clutter_text.connect('activate', () => {
            this._executeActiveSearch();
            this._activateSelected();
        });

        // Key Controller on entry for navigation & Enter launch
        const entryKeyController = new Clutter.KeyController();
        entryKeyController.connect('key-press', () => {
            const [, symbol] = entryKeyController.get_key();

            if (symbol === Clutter.KEY_Escape) {
                this.close();
                return Clutter.EVENT_STOP;
            }
            if (symbol === Clutter.KEY_Down) {
                this._selectNext();
                return Clutter.EVENT_STOP;
            }
            if (symbol === Clutter.KEY_Up) {
                this._selectPrevious();
                return Clutter.EVENT_STOP;
            }
            if (symbol === Clutter.KEY_Return || symbol === Clutter.KEY_KP_Enter || symbol === Clutter.KEY_ISO_Enter) {
                this._executeActiveSearch();
                this._activateSelected();
                return Clutter.EVENT_STOP;
            }

            return Clutter.EVENT_PROPAGATE;
        });
        this._entry.add_action(entryKeyController);

        searchBox.add_child(this._entry);

        const escBadge = new St.Label({
            text: 'ESC',
            style_class: 'tahoe-spotlight-esc-badge',
            y_align: Clutter.ActorAlign.CENTER,
        });
        searchBox.add_child(escBadge);

        mainContainer.add_child(searchBox);

        // 2. Glass Separator
        const separator = new St.Widget({
            style_class: 'tahoe-spotlight-separator',
        });
        mainContainer.add_child(separator);

        // 3. Scrollable Results List
        this._scrollView = new St.ScrollView({
            style_class: 'tahoe-spotlight-scrollview',
            hscrollbar_policy: St.PolicyType.NEVER,
            vscrollbar_policy: St.PolicyType.AUTOMATIC,
        });

        this._resultsBox = new St.BoxLayout({
            orientation: Clutter.Orientation.VERTICAL,
            style_class: 'tahoe-spotlight-results-box',
        });
        this._scrollView.add_child(this._resultsBox);
        mainContainer.add_child(this._scrollView);

        // 4. Footer Bar
        const footerBox = new St.BoxLayout({
            orientation: Clutter.Orientation.HORIZONTAL,
            style_class: 'tahoe-spotlight-footer',
            y_align: Clutter.ActorAlign.CENTER,
        });

        const hintLabel = new St.Label({
            text: '↑↓ Di chuyển  •  ↵ Mở ứng dụng  •  ESC Đóng',
            style_class: 'tahoe-spotlight-footer-hint',
            x_expand: true,
        });
        footerBox.add_child(hintLabel);

        const brandLabel = new St.Label({
            text: 'Spotlight Tahoe',
            style_class: 'tahoe-spotlight-footer-brand',
        });
        footerBox.add_child(brandLabel);

        mainContainer.add_child(footerBox);

        this.contentLayout.add_child(mainContainer);

        this.setInitialKeyFocus(this._entry.clutter_text);
    }

    _refreshAppIndex() {
        const appSys = Shell.AppSystem.get_default();
        const installed = appSys.get_installed() || [];
        this._indexedApps = [];

        for (const app of installed) {
            if (!shouldShowApp(app)) continue;

            const appInfo = app.app_info || (typeof app.get_app_info === 'function' ? app.get_app_info() : null);
            const rawName = (app.get_name() || '').toLowerCase();
            const cleanName = removeVietnameseDiacritics(rawName);
            const rawDesc = (app.get_description() || '').toLowerCase();
            const cleanDesc = removeVietnameseDiacritics(rawDesc);
            const idLower = (app.get_id() || '').toLowerCase();
            const words = cleanName.split(/[\s\-_]+/);

            // Extract keywords and categories from the desktop file
            const keywords = [];
            try {
                if (appInfo && typeof appInfo.get_keywords === 'function') {
                    const kws = appInfo.get_keywords() || [];
                    for (const k of kws) {
                        const ck = removeVietnameseDiacritics(k.toLowerCase().trim());
                        if (ck) keywords.push(ck);
                    }
                }
            } catch (e) {}

            try {
                if (appInfo && typeof appInfo.get_categories === 'function') {
                    const cats = (appInfo.get_categories() || '').toLowerCase().split(';');
                    for (const c of cats) {
                        const cc = removeVietnameseDiacritics(c.trim());
                        if (cc) keywords.push(cc);
                    }
                }
            } catch (e) {}

            this._indexedApps.push({
                app,
                id: app.get_id(),
                rawName,
                cleanName,
                rawDesc,
                cleanDesc,
                idLower,
                words,
                keywords,
            });
        }
    }

    _getCurrentQuery() {
        let text = '';
        try {
            const layout = this._entry.clutter_text.get_layout();
            if (layout) {
                text = layout.get_text() || '';
            }
        } catch (e) {}

        if (!text) {
            try {
                text = this._entry.clutter_text.get_text() || '';
            } catch (e) {}
        }

        if (!text) {
            try {
                text = this._entry.get_text() || '';
            } catch (e) {}
        }

        return text.trim();
    }

    _scheduleSearch() {
        if (this._debounceTimerId) {
            GLib.source_remove(this._debounceTimerId);
            this._debounceTimerId = 0;
        }

        // 60ms debounce for smooth non-blocking search
        this._debounceTimerId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 60, () => {
            this._debounceTimerId = 0;
            const query = this._getCurrentQuery();
            if (query !== this._lastQuery) {
                this._lastQuery = query;
                this._updateResults(query);
            }
            return GLib.SOURCE_REMOVE;
        });
    }

    _executeActiveSearch() {
        if (this._debounceTimerId) {
            GLib.source_remove(this._debounceTimerId);
            this._debounceTimerId = 0;
        }
        const query = this._getCurrentQuery();
        if (query !== this._lastQuery) {
            this._lastQuery = query;
            this._updateResults(query);
        }
    }

    open() {
        if (this.state === ModalDialog.State.OPENED || this.state === ModalDialog.State.OPENING)
            return;

        super.open();
        this._refreshAppIndex();
        this._entry.set_text('');
        this._lastQuery = '';
        this._updateResults('');

        GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
            this._entry.clutter_text.grab_key_focus();
            return GLib.SOURCE_REMOVE;
        });
    }

    close() {
        if (this._debounceTimerId) {
            GLib.source_remove(this._debounceTimerId);
            this._debounceTimerId = 0;
        }
        super.close();
    }

    toggle() {
        if (this.state === ModalDialog.State.OPENED || this.state === ModalDialog.State.OPENING) {
            this.close();
        } else {
            this.open();
        }
    }

    _updateResults(query) {
        this._resultsBox.destroy_all_children();
        this._results = [];
        this._itemWidgets = [];
        this._selectedIndex = 0;

        const trimmed = (query || '').trim();

        if (trimmed.length === 0) {
            this._results = this._getDefaultSuggestions();
        } else {
            // 1. Math Calculator
            const mathResult = this._tryEvaluateMath(trimmed);
            if (mathResult) {
                this._results.push(mathResult);
            }

            // 2. Applications Search (Pure Application Launcher)
            const appResults = this._searchApps(trimmed);
            this._results.push(...appResults);
        }

        if (this._results.length === 0) {
            const emptyBox = new St.BoxLayout({
                orientation: Clutter.Orientation.VERTICAL,
                style_class: 'tahoe-spotlight-empty-box',
                x_align: Clutter.ActorAlign.CENTER,
            });

            const emptyIcon = new St.Icon({
                icon_name: 'edit-find-symbolic',
                style_class: 'tahoe-spotlight-empty-icon',
            });
            emptyBox.add_child(emptyIcon);

            const emptyLabel = new St.Label({
                text: `Không tìm thấy ứng dụng nào cho "${trimmed}"`,
                style_class: 'tahoe-spotlight-empty-label',
            });
            emptyBox.add_child(emptyLabel);

            this._resultsBox.add_child(emptyBox);
            return;
        }

        const maxResults = this._settings ? this._settings.get_int('max-results') : 8;
        this._results = this._results.slice(0, Math.max(6, maxResults));

        // Render application rows
        this._results.forEach((item, index) => {
            const btn = new St.Button({
                style_class: 'tahoe-spotlight-item',
                reactive: true,
                can_focus: true,
                track_hover: true,
                button_mask: St.ButtonMask.PRIMARY | St.ButtonMask.ONE,
                x_expand: true,
            });

            const row = new St.BoxLayout({
                orientation: Clutter.Orientation.HORIZONTAL,
                style_class: 'tahoe-spotlight-item-box',
                x_expand: true,
                y_align: Clutter.ActorAlign.CENTER,
                reactive: false,
            });

            const iconBin = this._createItemIcon(item);
            iconBin.reactive = false;
            row.add_child(iconBin);

            const textBox = new St.BoxLayout({
                orientation: Clutter.Orientation.VERTICAL,
                x_expand: true,
                style_class: 'tahoe-spotlight-item-text-box',
                y_align: Clutter.ActorAlign.CENTER,
                reactive: false,
            });

            const titleLabel = new St.Label({
                text: item.title,
                style_class: 'tahoe-spotlight-item-title',
                reactive: false,
            });
            textBox.add_child(titleLabel);

            if (item.subtitle) {
                const subLabel = new St.Label({
                    text: item.subtitle,
                    style_class: 'tahoe-spotlight-item-sub',
                    reactive: false,
                });
                textBox.add_child(subLabel);
            }
            row.add_child(textBox);

            if (item.badge) {
                const badgeLabel = new St.Label({
                    text: item.badge,
                    style_class: 'tahoe-spotlight-item-badge',
                    y_align: Clutter.ActorAlign.CENTER,
                    reactive: false,
                });
                row.add_child(badgeLabel);
            }

            btn.set_child(row);

            // Handle click via both 'clicked' and 'button-release-event'
            btn.connect('clicked', () => {
                this._activateItem(index);
            });

            btn.connect('button-release-event', (actor, event) => {
                if (event.get_button() === 1) {
                    this._activateItem(index);
                    return Clutter.EVENT_STOP;
                }
                return Clutter.EVENT_PROPAGATE;
            });

            btn.connect('notify::hover', () => {
                if (btn.hover)
                    this._selectItem(index, false);
            });

            this._itemWidgets.push(btn);
            this._resultsBox.add_child(btn);
        });

        this._selectItem(0, false);
    }

    _createItemIcon(item) {
        const bin = new St.Bin({
            style_class: 'tahoe-spotlight-icon-bin',
            width: 42,
            height: 42,
            x_align: Clutter.ActorAlign.CENTER,
            y_align: Clutter.ActorAlign.CENTER,
        });

        let iconActor = null;
        if (item.app) {
            try {
                iconActor = item.app.create_icon_texture(36);
            } catch (e) {}

            if (!iconActor) {
                try {
                    const gicon = (typeof item.app.get_icon === 'function' ? item.app.get_icon() : null) ||
                                  (item.app.app_info ? item.app.app_info.get_icon() : null);
                    if (gicon) {
                        iconActor = new St.Icon({
                            gicon: gicon,
                            icon_size: 36,
                        });
                    }
                } catch (e) {}
            }
        }

        if (!iconActor) {
            iconActor = new St.Icon({
                icon_name: item.iconName || 'application-x-executable-symbolic',
                icon_size: 28,
                style_class: 'tahoe-spotlight-item-icon',
            });
        }

        bin.set_child(iconActor);
        return bin;
    }

    _selectItem(index, doScroll = true) {
        if (index < 0 || index >= this._itemWidgets.length)
            return;

        if (this._itemWidgets[this._selectedIndex]) {
            this._itemWidgets[this._selectedIndex].remove_style_class_name('selected');
        }

        this._selectedIndex = index;
        const targetBtn = this._itemWidgets[this._selectedIndex];
        if (targetBtn) {
            targetBtn.add_style_class_name('selected');
            if (doScroll) {
                scrollActorIntoView(this._scrollView, targetBtn);
            }
        }
    }

    _selectNext() {
        if (this._itemWidgets.length === 0) return;
        const next = (this._selectedIndex + 1) % this._itemWidgets.length;
        this._selectItem(next, true);
    }

    _selectPrevious() {
        if (this._itemWidgets.length === 0) return;
        const prev = (this._selectedIndex - 1 + this._itemWidgets.length) % this._itemWidgets.length;
        this._selectItem(prev, true);
    }

    _activateSelected() {
        this._activateItem(this._selectedIndex);
    }

    _activateItem(index) {
        const item = this._results[index];
        if (!item) return;

        // Close Spotlight
        this.close();

        // Authentic Launcher Behavior:
        // 1. If app is already open -> raise and focus the existing window (NEVER open duplicate window)
        // 2. If app is not running -> launch it
        try {
            if (item.app) {
                const app = item.app;
                const windows = (typeof app.get_windows === 'function' ? app.get_windows() : []) || [];

                if (windows.length > 0) {
                    // Focus existing open window
                    Main.activateWindow(windows[0]);
                    return;
                }

                // Launch app
                try {
                    app.activate();
                } catch (e1) {
                    const appInfo = app.app_info || Gio.DesktopAppInfo.new(app.get_id());
                    if (appInfo && typeof appInfo.launch === 'function') {
                        appInfo.launch([], null);
                    }
                }
            } else if (item.action) {
                item.action();
            }
        } catch (err) {
            console.error('[UbuntuTahoeSpotlight] App launch error:', err);
            try {
                if (item?.app) {
                    const appInfo = Gio.DesktopAppInfo.new(item.app.get_id());
                    if (appInfo) {
                        appInfo.launch([], null);
                    }
                }
            } catch (e2) {}
        }
    }

    _tryEvaluateMath(query) {
        const trimmed = query.trim();
        if (!/^[0-9+\-*/%().\s^]+$/.test(trimmed))
            return null;
        if (!/[+\-*/%^]/.test(trimmed))
            return null;

        try {
            const expr = trimmed.replace(/\^/g, '**');
            const fn = new Function(`'use strict'; return (${expr});`);
            const res = fn();

            if (typeof res === 'number' && Number.isFinite(res)) {
                let formatted;
                if (Number.isInteger(res)) {
                    formatted = res.toLocaleString('vi-VN');
                } else {
                    formatted = parseFloat(res.toFixed(6)).toLocaleString('vi-VN');
                }

                return {
                    title: `= ${formatted}`,
                    subtitle: `Tính: ${trimmed} (Nhấn Enter để sao chép)`,
                    badge: 'MÁY TÍNH',
                    iconName: 'accessories-calculator-symbolic',
                    action: () => {
                        St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, String(res));
                        Main.notify('Spotlight', `Đã sao chép kết quả: ${formatted}`);
                    },
                };
            }
        } catch (e) {}
        return null;
    }

    _searchApps(query) {
        const rawQ = query.toLowerCase().trim();
        const cleanQ = removeVietnameseDiacritics(rawQ);
        if (!cleanQ) return [];

        if (!this._indexedApps) {
            this._refreshAppIndex();
        }

        const scoredApps = [];

        // Scored search matching name, words, keywords & categories from .desktop files
        for (const item of this._indexedApps) {
            let score = 0;

            if (item.rawName === rawQ || item.cleanName === cleanQ) {
                score = 100;
            } else if (item.idLower === rawQ || item.idLower === rawQ + '.desktop') {
                score = 95;
            } else if (item.rawName.startsWith(rawQ) || item.cleanName.startsWith(cleanQ)) {
                score = 90;
            } else if (item.words.some(w => w.startsWith(cleanQ))) {
                score = 80;
            } else if (item.keywords.some(k => k.startsWith(cleanQ) || cleanQ.startsWith(k))) {
                score = 75;
            } else if (item.idLower.includes(cleanQ)) {
                score = 60;
            } else if (item.cleanName.includes(cleanQ)) {
                score = 50;
            } else if (item.cleanDesc.includes(cleanQ)) {
                score = 40;
            }

            if (score > 0) {
                const isRunning = item.app.state !== Shell.AppState.STOPPED;
                const finalScore = score + (isRunning ? 5 : 0);
                scoredApps.push({ app: item.app, score: finalScore });
            }
        }

        scoredApps.sort((a, b) => b.score - a.score);

        return scoredApps.map(({ app }) => {
            const isRunning = app.state !== Shell.AppState.STOPPED;
            return {
                title: app.get_name(),
                subtitle: isRunning ? 'Đang chạy' : (app.get_description() || 'Ứng dụng'),
                badge: isRunning ? 'ĐANG CHẠY' : 'ỨNG DỤNG',
                app: app,
            };
        });
    }

    _getDefaultSuggestions() {
        const results = [];
        const appSys = Shell.AppSystem.get_default();

        // Display favorite apps from Dock / Dash
        try {
            const favIds = global.settings.get_strv('favorite-apps') || [];
            for (const id of favIds) {
                const app = appSys.lookup_app(id);
                if (app && shouldShowApp(app)) {
                    const isRunning = app.state !== Shell.AppState.STOPPED;
                    results.push({
                        title: app.get_name(),
                        subtitle: isRunning ? 'Đang chạy' : (app.get_description() || 'Ứng dụng yêu thích'),
                        badge: isRunning ? 'ĐANG CHẠY' : 'YÊU THÍCH',
                        app: app,
                    });
                }
            }
        } catch (e) {}

        return results;
    }

    destroy() {
        if (this._debounceTimerId) {
            GLib.source_remove(this._debounceTimerId);
            this._debounceTimerId = 0;
        }
        if (this.state === ModalDialog.State.OPENED || this.state === ModalDialog.State.OPENING) {
            this.close();
        }
        super.destroy();
    }
});

export default class UbuntuTahoeSpotlightExtension extends Extension {
    enable() {
        console.log('[UbuntuTahoeSpotlight] Enabling extension...');
        this._settings = this.getSettings();
        this._dialog = new SpotlightDialog(this);

        this._bindShortcut();
        console.log('[UbuntuTahoeSpotlight] Enabled successfully.');
    }

    _bindShortcut() {
        try {
            const current = this._settings.get_strv('toggle-spotlight');
            if (!current || current.length === 0) {
                this._settings.set_strv('toggle-spotlight', ['<Super><Alt>f']);
            }
        } catch (e) {}

        try {
            Main.wm.addKeybinding(
                'toggle-spotlight',
                this._settings,
                Meta.KeyBindingFlags.IGNORE_AUTOREPEAT,
                Shell.ActionMode.ALL,
                () => {
                    this._dialog.toggle();
                }
            );
        } catch (e) {
            console.error('[UbuntuTahoeSpotlight] Failed to bind shortcut:', e);
        }
    }

    _unbindShortcut() {
        try {
            Main.wm.removeKeybinding('toggle-spotlight');
        } catch (e) {}
    }

    disable() {
        console.log('[UbuntuTahoeSpotlight] Disabling extension...');
        this._unbindShortcut();

        if (this._dialog) {
            this._dialog.destroy();
            this._dialog = null;
        }
        this._settings = null;
    }
}
