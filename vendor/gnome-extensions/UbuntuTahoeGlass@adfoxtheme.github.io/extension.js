import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {DockWatcher} from './dist/dockManager.js';
import {ApplicationManager} from './dist/applicationManager.js';
import {WindowListService} from './dist/windowListService.js';
import {Logger, setUtilsLogger} from './dist/logger.js';
import {adaptiveColorTweener} from './dist/animation.js';
import {installGlassDiagnostics, removeGlassDiagnostics} from './dist/diagnostics.js';
import {trackViewPaints, untrackViewPaints} from './dist/rendering/backdropGlass.js';
import {clearShaderSources} from './dist/rendering/pipelines.js';

export default class UbuntuTahoeGlassExtension extends Extension {
  enable() {
    this._settings = this.getSettings();
    this._logger = new Logger(this._settings);
    setUtilsLogger(this._logger);
    installGlassDiagnostics();
    trackViewPaints();

    const path = this.dir.get_path();

    // 1. Application Windows Glass
    try {
      this._applicationManager = new ApplicationManager(path, this._settings, this._logger);
      this._applicationManager.setup();
    } catch (err) {
      console.error('[UbuntuTahoeGlass] Error initializing ApplicationManager:', err);
    }

    try {
      this._windowListService = new WindowListService(this._logger);
      this._windowListService.setup();
    } catch (err) {
      console.error('[UbuntuTahoeGlass] Error initializing WindowListService:', err);
    }

    // 2. Dock Glass
    const dummyIconWatcher = {
      watchDock() {},
      unwatchDock() {},
    };

    try {
      this._dockWatcher = new DockWatcher(path, this._settings, this._logger, dummyIconWatcher);
      this._dockWatcher.setup();
    } catch (err) {
      console.error('[UbuntuTahoeGlass] Error initializing DockWatcher:', err);
    }
  }

  disable() {
    try {
      adaptiveColorTweener.stopAll();
    } catch (e) {}

    if (this._dockWatcher) {
      try {
        this._dockWatcher.cleanup();
      } catch (e) {}
      this._dockWatcher = null;
    }

    if (this._applicationManager) {
      try {
        this._applicationManager.cleanup();
      } catch (e) {}
      this._applicationManager = null;
    }

    if (this._windowListService) {
      try {
        this._windowListService.cleanup();
      } catch (e) {}
      this._windowListService = null;
    }

    try {
      untrackViewPaints();
      removeGlassDiagnostics();
      clearShaderSources();
    } catch (e) {}

    this._settings = null;
    this._logger = null;
  }
}
