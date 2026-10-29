import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as AnimationUtils from 'resource:///org/gnome/shell/misc/animationUtils.js';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

function scrollItemIntoView(scrollView, actor) {
    if (!scrollView || !actor) return;
    try {
        if (typeof AnimationUtils?.ensureActorVisibleInScrollView === 'function') {
            AnimationUtils.ensureActorVisibleInScrollView(scrollView, actor);
            return;
        }
    } catch (e) {}
    try {
        const vadj = scrollView.vadjustment || scrollView.get_vscroll_bar()?.get_adjustment();
        if (!vadj) return;
        const [success, , y] = actor.transform_stage_point(0, 0);
        const [sSuccess, , sY] = scrollView.transform_stage_point(0, 0);
        if (success && sSuccess) {
            const relY = y - sY;
            if (relY < 0) vadj.value += relY;
            else if (relY + actor.height > scrollView.height) {
                vadj.value += (relY + actor.height - scrollView.height);
            }
        }
    } catch (e) {}
}

const HISTORY_PATH = GLib.build_filenamev([GLib.get_user_data_dir(), 'clipboard-manager', 'history.json']);

const ClipboardItem = GObject.registerClass(
class ClipboardItem extends PopupMenu.PopupBaseMenuItem {
    _init(entry, onActivate, onDelete) {
        super._init({
            reactive: true,
            can_focus: true,
            style_class: 'tahoe-clip-menu-item',
        });

        this.entry = entry;
        this.onActivate = onActivate;
        this.onDelete = onDelete;

        const box = new St.BoxLayout({
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'tahoe-clip-item-box',
        });

        const icon = new St.Icon({
            icon_name: 'edit-copy-symbolic',
            style_class: 'popup-menu-icon tahoe-clip-item-icon',
        });
        box.add_child(icon);

        let previewText = (entry.text || '').trim().replace(/[\r\n\t]+/g, ' ');
        if (previewText.length > 50) {
            previewText = previewText.slice(0, 48) + '...';
        }

        const label = new St.Label({
            text: previewText,
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'tahoe-clip-label',
        });
        box.add_child(label);

        const delBtn = new St.Button({
            style_class: 'button tahoe-clip-delete-btn',
            can_focus: true,
            child: new St.Icon({
                icon_name: 'user-trash-symbolic',
                icon_size: 14,
            }),
        });
        delBtn.connect('clicked', () => {
            if (this.onDelete) this.onDelete(this.entry);
            return Clutter.EVENT_STOP;
        });
        box.add_child(delBtn);

        this.add_child(box);

        this.connect('activate', () => {
            if (this.onActivate) this.onActivate(this.entry);
        });
    }
});

const ClipboardIndicator = GObject.registerClass(
class ClipboardIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.5, 'UbuntuTahoeClipboard');

        this._extension = extension;
        this._settings = extension.getSettings();
        this._historyPath = HISTORY_PATH;
        this._lastCopiedText = null;
        this._history = this._loadHistory();

        // Icon on Top Bar
        this._icon = new St.Icon({
            icon_name: 'edit-copy-symbolic',
            style_class: 'system-status-icon',
        });
        this.add_child(this._icon);

        // Build Popup Menu
        this._buildMenu();

        // Listen for Global Clipboard Changes
        const selection = global.display.get_selection();
        this._selectionOwnerChangedId = selection.connect('owner-changed', (_sel, type) => {
            if (type === Meta.SelectionType.SELECTION_CLIPBOARD) {
                St.Clipboard.get_default().get_text(St.ClipboardType.CLIPBOARD, (_clip, text) => {
                    if (text && text.trim().length > 0 && text !== this._lastCopiedText) {
                        this._lastCopiedText = text;
                        this._addEntry(text);
                    }
                });
            }
        });

        // Keybinding for Super + V (Win + V)
        this._bindShortcut();

        this.menu.connect('open-state-changed', (_menu, open) => {
            if (open) {
                if (this._searchEntry) {
                    this._searchEntry.set_text('');
                    this._searchEntry.grab_key_focus();
                }
                this._renderItems('');
            }
        });
    }

    _buildMenu() {
        this.menu.removeAll();

        // 1. Header (Title + Clear All button)
        const headerItem = new PopupMenu.PopupBaseMenuItem({
            reactive: false,
            can_focus: false,
            style_class: 'tahoe-clip-header-item',
        });

        const headerBox = new St.BoxLayout({
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'tahoe-clip-header-box',
        });

        this._headerLabel = new St.Label({
            text: `Bảng nhớ tạm (${this._history.length}/20)`,
            x_expand: true,
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'tahoe-clip-header-title',
        });
        headerBox.add_child(this._headerLabel);

        const clearBtn = new St.Button({
            style_class: 'button tahoe-clip-delete-btn',
            can_focus: true,
            child: new St.Icon({
                icon_name: 'user-trash-symbolic',
                icon_size: 14,
            }),
        });
        clearBtn.connect('clicked', () => {
            this._clearAll();
            return Clutter.EVENT_STOP;
        });
        headerBox.add_child(clearBtn);

        headerItem.add_child(headerBox);
        this.menu.addMenuItem(headerItem);

        // 2. Search Entry
        const searchItem = new PopupMenu.PopupBaseMenuItem({
            reactive: false,
            can_focus: false,
            style_class: 'tahoe-clip-search-item',
        });
        this._searchEntry = new St.Entry({
            hint_text: 'Tìm kiếm lịch sử (Win + Alt + Space)...',
            x_expand: true,
            style_class: 'tahoe-clip-search-entry search-entry',
        });
        this._searchEntry.clutter_text.connect('text-changed', () => {
            const query = this._searchEntry.get_text().trim();
            this._renderItems(query);
        });
        searchItem.add_child(this._searchEntry);
        this.menu.addMenuItem(searchItem);

        // Separator
        const sep = new PopupMenu.PopupSeparatorMenuItem();
        sep.actor.add_style_class_name('tahoe-clip-separator');
        this.menu.addMenuItem(sep);

        // 3. Scrollable List Section
        this._listSection = new PopupMenu.PopupMenuSection();

        this._scrollView = new St.ScrollView({
            style_class: 'tahoe-clip-scrollview',
            style: 'max-height: 400px;',
            hscrollbar_policy: St.PolicyType.NEVER,
            vscrollbar_policy: St.PolicyType.AUTOMATIC,
            overlay_scrollbars: false,
            child: this._listSection.box,
        });
        this._scrollView._delegate = this._listSection;
        this._listSection.actor = this._scrollView;

        const vscroll = this._scrollView.get_vscroll_bar();
        if (vscroll) {
            vscroll.add_style_class_name('tahoe-clip-scrollbar');
            for (const child of vscroll.get_children()) {
                if (child.name === 'trough') {
                    child.add_style_class_name('tahoe-clip-trough');
                } else {
                    child.name = 'vhandle';
                    child.add_style_class_name('tahoe-clip-handle');
                }
            }
        }

        this.menu.addMenuItem(this._listSection);

        this._renderItems('');
    }

    _renderItems(filterQuery = '') {
        this._listSection.removeAll();

        let filtered = this._history;
        if (filterQuery) {
            const q = filterQuery.toLowerCase();
            filtered = this._history.filter(item => (item.text || '').toLowerCase().includes(q));
        }

        if (this._headerLabel) {
            this._headerLabel.set_text(`Bảng nhớ tạm (${this._history.length}/20)`);
        }

        if (filtered.length === 0) {
            const emptyItem = new PopupMenu.PopupMenuItem(
                filterQuery ? 'Không tìm thấy kết quả phù hợp' : 'Chưa có nội dung sao chép',
                { reactive: false, style_class: 'tahoe-clip-menu-item' }
            );
            this._listSection.addMenuItem(emptyItem);
            return;
        }

        filtered.forEach(entry => {
            const item = new ClipboardItem(
                entry,
                (target) => this._copyItem(target),
                (target) => this._deleteItem(target)
            );
            // Only auto-scroll when navigating via keyboard (arrow keys), NOT on mouse motion!
            item.connect('notify::active', () => {
                const event = Clutter.get_current_event();
                if (item.active && event && event.type() === Clutter.EventType.KEY_PRESS) {
                    scrollItemIntoView(this._scrollView, item);
                }
            });
            this._listSection.addMenuItem(item);
        });
    }

    _addEntry(text) {
        if (!text || text.trim().length === 0) return;

        this._history = this._history.filter(item => item.text !== text);
        this._history.unshift({
            text: text,
            timestamp: Math.floor(Date.now() / 1000),
            length: text.length,
        });

        const maxItems = 20;
        if (this._history.length > maxItems) {
            this._history = this._history.slice(0, maxItems);
        }

        this._saveHistory();
        this._renderItems(this._searchEntry ? this._searchEntry.get_text() : '');
    }

    _copyItem(entry) {
        this._lastCopiedText = entry.text;
        St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, entry.text);

        // Move to top of history
        this._history = this._history.filter(item => item.text !== entry.text);
        this._history.unshift(entry);
        this._saveHistory();

        this.menu.close();
    }

    _deleteItem(entry) {
        this._history = this._history.filter(item => item.text !== entry.text);
        this._saveHistory();
        this._renderItems(this._searchEntry ? this._searchEntry.get_text() : '');
    }

    _clearAll() {
        this._history = [];
        this._saveHistory();
        this._renderItems('');
    }

    _loadHistory() {
        try {
            if (GLib.file_test(this._historyPath, GLib.FileTest.EXISTS)) {
                const [ok, bytes] = GLib.file_get_contents(this._historyPath);
                if (ok) {
                    const decoder = new TextDecoder('utf-8');
                    const data = JSON.parse(decoder.decode(bytes));
                    return Array.isArray(data) ? data.slice(0, 20) : [];
                }
            }
        } catch (e) {
            console.error('[UbuntuTahoeClipboard] Error loading history:', e);
        }
        return [];
    }

    _saveHistory() {
        try {
            const dir = GLib.path_get_dirname(this._historyPath);
            GLib.mkdir_with_parents(dir, 0o755);
            const jsonStr = JSON.stringify(this._history, null, 2);
            GLib.file_set_contents(this._historyPath, jsonStr);
        } catch (e) {
            console.error('[UbuntuTahoeClipboard] Error saving history:', e);
        }
    }

    _bindShortcut() {
        // 1. Permanently remove conflict from GNOME default message tray
        try {
            const gnomeKeybindings = new Gio.Settings({ schema_id: 'org.gnome.shell.keybindings' });
            const msgTray = gnomeKeybindings.get_strv('toggle-message-tray');
            if (msgTray.includes('<Super>v')) {
                const filtered = msgTray.filter(k => k !== '<Super>v');
                gnomeKeybindings.set_strv('toggle-message-tray', filtered.length > 0 ? filtered : ['<Super>m']);
            }
        } catch (e) {}

        // 2. Default to Super + Alt + Space
        try {
            const current = this._settings.get_strv('toggle-menu');
            if (!current || current.length === 0 || current.includes('<Super>v')) {
                this._settings.set_strv('toggle-menu', ['<Super><Alt>space']);
            }
        } catch (e) {}

        // 3. Register global keybinding across ALL modes (NORMAL, OVERVIEW, POPUP, MODAL, FULLSCREEN)
        try {
            Main.wm.addKeybinding(
                'toggle-menu',
                this._settings,
                Meta.KeyBindingFlags.IGNORE_AUTOREPEAT,
                Shell.ActionMode.ALL,
                () => {
                    this.menu.toggle();
                }
            );
        } catch (e) {
            console.error('[UbuntuTahoeClipboard] Failed to bind shortcut:', e);
        }
    }

    _unbindShortcut() {
        try {
            Main.wm.removeKeybinding('toggle-menu');
        } catch (e) {}
    }

    destroy() {
        this._unbindShortcut();

        if (this._selectionOwnerChangedId) {
            const selection = global.display.get_selection();
            selection.disconnect(this._selectionOwnerChangedId);
            this._selectionOwnerChangedId = null;
        }

        super.destroy();
    }
});

export default class UbuntuTahoeClipboardExtension extends Extension {
    enable() {
        console.log('[UbuntuTahoeClipboard] Enabling extension...');
        this._indicator = new ClipboardIndicator(this);
        Main.panel.addToStatusArea('UbuntuTahoeClipboard', this._indicator);
        console.log('[UbuntuTahoeClipboard] Enabled successfully.');
    }

    disable() {
        console.log('[UbuntuTahoeClipboard] Disabling extension...');
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }
}
