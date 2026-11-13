import GLib from 'gi://GLib';
import Gio from 'gi://Gio';

let prevCpu = null;
let prevNet = null;
let cpuModelCache = null;
let gpuType = null;
let amdPath = null;
let gpuModelName = null;
let gpuInfoCache = {
    hasGpu: false,
    util: 0,
    temp: null,
    used: 0,
    total: 0,
    model: '',
};

function readFile(path) {
    try {
        const [ok, bytes] = GLib.file_get_contents(path);
        if (ok) {
            return new TextDecoder('utf-8').decode(bytes);
        }
    } catch (e) {
        // ignore
    }
    return '';
}

function getCpuModel() {
    if (cpuModelCache) return cpuModelCache;
    const cpuinfo = readFile('/proc/cpuinfo');
    for (const line of cpuinfo.split('\n')) {
        if (line.startsWith('model name')) {
            const parts = line.split(':');
            if (parts.length > 1) {
                let name = parts[1].trim();
                name = name.replace(/CPU\s+@.*$/, '').trim();
                name = name.replace(/Intel\(R\)\s+Core\(TM\)\s+/, '');
                name = name.replace(/Intel\(R\)\s+Xeon\(R\)\s+CPU\s+/, 'Xeon ');
                cpuModelCache = name;
                return name;
            }
        }
    }
    cpuModelCache = 'Intel / AMD';
    return cpuModelCache;
}

function getCpuTemp() {
    const raw = readFile('/sys/class/thermal/thermal_zone0/temp');
    if (raw) {
        const val = parseInt(raw.trim(), 10);
        if (!isNaN(val)) return Math.round(val / 1000);
    }
    return null;
}

function readCpuStat() {
    const stat = readFile('/proc/stat');
    const firstLine = stat.split('\n')[0];
    if (!firstLine || !firstLine.startsWith('cpu ')) return { percent: 0 };
    const parts = firstLine.trim().split(/\s+/).slice(1).map(Number);
    // [user, nice, system, idle, iowait, irq, softirq, steal]
    const idle = parts[3] + (parts[4] || 0);
    const total = parts.reduce((a, b) => a + b, 0);

    let percent = 0;
    if (prevCpu) {
        const deltaIdle = idle - prevCpu.idle;
        const deltaTotal = total - prevCpu.total;
        if (deltaTotal > 0) {
            percent = Math.max(0, Math.min(100, Math.round(((deltaTotal - deltaIdle) / deltaTotal) * 100)));
        }
    }
    prevCpu = { idle, total };
    return percent;
}

function readMem() {
    const meminfo = readFile('/proc/meminfo');
    let total = 0, avail = 0, swapTotal = 0, swapFree = 0;
    for (const line of meminfo.split('\n')) {
        if (line.startsWith('MemTotal:')) total = parseInt(line.replace(/\D+/g, ''), 10);
        if (line.startsWith('MemAvailable:')) avail = parseInt(line.replace(/\D+/g, ''), 10);
        if (line.startsWith('SwapTotal:')) swapTotal = parseInt(line.replace(/\D+/g, ''), 10);
        if (line.startsWith('SwapFree:')) swapFree = parseInt(line.replace(/\D+/g, ''), 10);
    }
    const used = total - avail;
    const percent = total > 0 ? Math.round((used / total) * 100) : 0;
    const swapUsed = swapTotal - swapFree;
    const swapPercent = swapTotal > 0 ? Math.round((swapUsed / swapTotal) * 100) : 0;

    const usedGiB = (used / 1024 / 1024).toFixed(1);
    const totalGiB = (total / 1024 / 1024).toFixed(1);

    return {
        percent,
        text: `${usedGiB} / ${totalGiB} GiB`,
        swapPercent,
    };
}

function readDisk() {
    try {
        const file = Gio.File.new_for_path('/');
        const info = file.query_filesystem_info('filesystem::size,filesystem::free', null);
        const total = info.get_attribute_uint64('filesystem::size');
        const free = info.get_attribute_uint64('filesystem::free');
        const used = total - free;
        const percent = total > 0 ? Math.round((used / total) * 100) : 0;
        const usedGiB = (used / 1024 / 1024 / 1024).toFixed(1);
        const totalGiB = (total / 1024 / 1024 / 1024).toFixed(1);
        return { percent, text: `${usedGiB} / ${totalGiB} GiB` };
    } catch (e) {
        return { percent: 0, text: '-- / --' };
    }
}

function readNet() {
    const netdev = readFile('/proc/net/dev');
    let rxBytes = 0, txBytes = 0;
    let mainIf = '';

    for (const line of netdev.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('Inter-') || trimmed.startsWith('face')) continue;
        const parts = trimmed.split(':');
        if (parts.length < 2) continue;
        const ifName = parts[0].trim();
        if (ifName === 'lo') continue;

        const numbers = parts[1].trim().split(/\s+/).map(Number);
        if (numbers.length >= 9) {
            rxBytes += numbers[0];
            txBytes += numbers[8];
            if (!mainIf) mainIf = ifName;
        }
    }

    const now = GLib.get_monotonic_time() / 1000000; // seconds
    let downSpeed = 0;
    let upSpeed = 0;

    if (prevNet) {
        const dt = now - prevNet.time;
        if (dt > 0.3) {
            downSpeed = Math.max(0, (rxBytes - prevNet.rx) / dt / 1024); // KB/s
            upSpeed = Math.max(0, (txBytes - prevNet.tx) / dt / 1024); // KB/s
        }
    }
    prevNet = { rx: rxBytes, tx: txBytes, time: now };

    const formatSpeed = (val) => {
        if (val >= 1024) return `${(val / 1024).toFixed(1)} MB/s`;
        return `${Math.round(val)} KB/s`;
    };

    return {
        interface: mainIf,
        downText: formatSpeed(downSpeed),
        upText: formatSpeed(upSpeed),
    };
}

function getAmdModel() {
    if (gpuModelName) return gpuModelName;
    try {
        const [ok, stdout] = GLib.spawn_command_line_sync('lspci');
        if (ok && stdout) {
            const text = new TextDecoder().decode(stdout);
            for (const line of text.split('\n')) {
                if (/vga|3d|display/i.test(line) && /amd|radeon|advanced micro/i.test(line)) {
                    const bracketMatch = line.match(/\[(.*?)\]/g);
                    if (bracketMatch && bracketMatch.length > 0) {
                        for (const b of bracketMatch) {
                            const inner = b.slice(1, -1).trim();
                            if (/radeon/i.test(inner)) {
                                gpuModelName = inner.replace(/^Radeon\s+/i, 'RX ').replace(/Radeon\s+/i, '').trim();
                                return gpuModelName;
                            }
                        }
                    }
                    const afterColon = line.split(':').slice(2).join(':').trim();
                    if (afterColon) {
                        gpuModelName = afterColon
                            .replace(/Advanced Micro Devices, Inc\.\s*/i, '')
                            .replace(/\[AMD\/ATI\]\s*/i, '')
                            .replace(/\s*\(rev.*$/, '')
                            .trim();
                        return gpuModelName;
                    }
                }
            }
        }
    } catch (e) {}
    gpuModelName = 'Radeon GPU';
    return gpuModelName;
}

function getAmdTemp(basePath) {
    try {
        const hwmonDir = Gio.File.new_for_path(`${basePath}/hwmon`);
        const iter = hwmonDir.enumerate_children('standard::name', Gio.FileQueryInfoFlags.NONE, null);
        let info;
        while ((info = iter.next_file(null)) !== null) {
            const name = info.get_name();
            const tempRaw = readFile(`${basePath}/hwmon/${name}/temp1_input`).trim();
            if (tempRaw) {
                const val = parseInt(tempRaw, 10);
                if (!isNaN(val)) return Math.round(val / 1000);
            }
        }
    } catch (e) {}
    return null;
}

function detectGpuDevice() {
    if (gpuType !== null) return;

    // 1. Check for NVIDIA discrete GPU
    if (GLib.find_program_in_path('nvidia-smi')) {
        gpuType = 'nvidia';
        gpuInfoCache.hasGpu = true;
        return;
    }

    // 2. Check for AMD discrete GPU via sysfs (/sys/class/drm/card*/device)
    for (let i = 0; i < 8; i++) {
        const base = `/sys/class/drm/card${i}/device`;
        const vendor = readFile(`${base}/vendor`).trim().toLowerCase();
        if (vendor === '0x1002') {
            const vramRaw = readFile(`${base}/mem_info_vram_total`).trim();
            const vramBytes = parseInt(vramRaw, 10) || 0;
            // Discrete AMD GPUs have dedicated VRAM >= 1GB (1073741824 bytes)
            // Integrated APU graphics have 0 or <= 512MB
            if (vramBytes >= 1024 * 1024 * 1024) {
                gpuType = 'amd';
                amdPath = base;
                gpuInfoCache.hasGpu = true;
                gpuInfoCache.total = Math.round(vramBytes / (1024 * 1024));
                gpuInfoCache.model = getAmdModel();
                return;
            }
        }
    }

    // 3. No discrete GPU found (onboard Intel/AMD APU or virtual GPU)
    gpuType = 'none';
    gpuInfoCache.hasGpu = false;
}

function updateAmdGpu() {
    if (!amdPath) return;
    try {
        const busyRaw = readFile(`${amdPath}/gpu_busy_percent`).trim();
        const util = parseInt(busyRaw, 10);
        if (!isNaN(util)) gpuInfoCache.util = Math.max(0, Math.min(100, util));

        const usedRaw = readFile(`${amdPath}/mem_info_vram_used`).trim();
        const usedBytes = parseInt(usedRaw, 10);
        if (!isNaN(usedBytes)) {
            gpuInfoCache.used = Math.round(usedBytes / (1024 * 1024));
        }

        if (!gpuInfoCache.total) {
            const totalRaw = readFile(`${amdPath}/mem_info_vram_total`).trim();
            const totalBytes = parseInt(totalRaw, 10);
            if (!isNaN(totalBytes)) {
                gpuInfoCache.total = Math.round(totalBytes / (1024 * 1024));
            }
        }

        gpuInfoCache.temp = getAmdTemp(amdPath);
    } catch (e) {}
}

function updateNvidiaGpuAsync() {
    if (!GLib.find_program_in_path('nvidia-smi')) return;
    try {
        const proc = Gio.Subprocess.new(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name', '--format=csv,noheader,nounits'],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE
        );
        proc.communicate_utf8_async(null, null, (p, res) => {
            try {
                const [, stdout] = p.communicate_utf8_finish(res);
                if (stdout) {
                    const parts = stdout.trim().split(',').map(s => s.trim());
                    if (parts.length >= 4) {
                        gpuInfoCache = {
                            hasGpu: true,
                            util: parseInt(parts[0], 10) || 0,
                            used: parseInt(parts[1], 10) || 0,
                            total: parseInt(parts[2], 10) || 0,
                            temp: parseInt(parts[3], 10) || null,
                            model: parts[4] ? parts[4].replace(/NVIDIA\s+GeForce\s+/, '').replace(/NVIDIA\s+/, '') : 'GPU',
                        };
                    }
                }
            } catch (err) {
                // ignore
            }
        });
    } catch (e) {
        // ignore
    }
}

function updateGpu() {
    detectGpuDevice();
    if (gpuType === 'nvidia') {
        updateNvidiaGpuAsync();
    } else if (gpuType === 'amd') {
        updateAmdGpu();
    }
}

export function readSystemMetrics() {
    const uptimeSec = parseFloat(readFile('/proc/uptime').split(' ')[0]) || 0;
    const hours = Math.floor(uptimeSec / 3600);
    const minutes = Math.floor((uptimeSec % 3600) / 60);
    const seconds = Math.floor(uptimeSec % 60);
    const uptimeText = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    const cpuPercent = readCpuStat();
    const cpuTemp = getCpuTemp();
    const cpuModel = getCpuModel();

    const mem = readMem();
    const disk = readDisk();
    const net = readNet();

    updateGpu();

    return {
        uptime: uptimeText,
        uptimeSeconds: uptimeSec,
        cpu: {
            percent: cpuPercent,
            model: cpuModel,
            temp: cpuTemp,
        },
        gpu: gpuInfoCache,
        ram: mem,
        disk,
        net,
    };
}
