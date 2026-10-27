# MacTahoe cho GNOME và Xfce

Bộ giao diện macOS Tahoe cho GNOME và Xfce, kèm các tiện ích mở rộng độc quyền dành cho GNOME.

> [!NOTE]
> **Hệ điều hành hỗ trợ & đã kiểm thử thực tế (Tested):**
> - **Ubuntu 26.04** (GNOME 48 trở lên)
> - **Debian 13 (Trixie)** (GNOME 48 trở lên)
> - **Fedora 40, 41, 42+** (GNOME 48 trở lên)
> - **CachyOS GNOME / Arch Linux** (GNOME 48 trở lên)

## Kali Linux (GNOME và Xfce)

Đã bổ sung mã hỗ trợ Kali; cần kiểm thử thực tế trên máy Kali. Chạy `./install.sh` bằng tài khoản thường trong desktop đang dùng. Bộ cài tự nhận diện qua biến môi trường phiên đăng nhập.

| Desktop | Thành phần được áp dụng |
| --- | --- |
| GNOME 48+ | GTK, icon, con trỏ, font, wallpaper, ứng dụng, Firefox và các extension dock/widget |
| Xfce X11 (Kali/Ubuntu/Debian) | GTK/Xfwm4, icon, con trỏ, font, wallpaper, ứng dụng, Firefox, Plank dock và widget desktop |

Xfce dùng Plank dock với theme Tahoe: tự ẩn khi cửa sổ phóng to, phóng icon khi rê chuột, ghim ứng dụng và nút Launchpad mở `xfce4-appfinder`. Widget Python/GTK3 chạy riêng, có đồng hồ, thời tiết, CPU/GPU/RAM/ổ đĩa/mạng, âm lịch và nhắc nghỉ. GNOME tiếp tục dùng các extension hiện có. Dock/widget Xfce cần **X11**, chưa hỗ trợ Xfce Wayland.

Mở **MacTahoe · Widget & Dock** trong menu hoặc chạy `mactahoe-xfce-widgets --preferences` để bật/tắt từng widget, chọn thành phố/API key, chu kỳ cập nhật, thời gian nghỉ, màn hình và lề. Nút cài đặt Dock mở tùy chọn Plank; có thể chạy `mactahoe-xfce-dock preferences`. Thời tiết mặc định dùng Open-Meteo, API key OpenWeather là tùy chọn. GPU tự ẩn nếu không có telemetry AMD/NVIDIA; âm lịch dùng UTC+7.

Dock/widget tự chạy khi đăng nhập Xfce. Icon desktop được ẩn để nhường chỗ cho widget, cấu hình ban đầu được sao lưu để khôi phục khi gỡ. Panel Xfce hiện tại được giữ lại; nếu đã có panel/dock ở đáy màn hình, tắt panel/dock đó trong **Panel Preferences** để tránh trùng với Plank. Cài lại giữ cấu hình dock đã chỉnh. Không tự cài GNOME hay đổi display manager.

### Giao diện đăng nhập LightDM (Xfce)

Sau `./install.sh`, chạy riêng:

```bash
./install-lightdm.sh
```

Cần LightDM đang được cấu hình làm display manager và dùng **LightDM GTK Greeter** (Kali Xfce thông thường). Script kiểm tra greeter trước khi ghi, cài theme GTK Tahoe, con trỏ, font và wallpaper vào thư mục hệ thống đọc được trước đăng nhập. Giữ thiết lập bàn phím, accessibility và chính sách đăng nhập hiện có; không chuyển greeter, không restart phiên đang chạy. Khởi động lại khi muốn kiểm tra màn hình đăng nhập.

Khôi phục riêng, kể cả từ TTY bằng tài khoản thường:

```bash
./install-lightdm.sh --uninstall
```

Bản sao gốc được giữ tại `/var/lib/mactahoe-lightdm` bằng quyền root, cài lại không ghi đè bản sao này. `./uninstall.sh` cũng khôi phục LightDM nếu đã cài bằng tài khoản này. `install-gdm.sh` vẫn dành cho GNOME/GDM.

Đã kiểm tra widget bằng GTK/X11 và Xfwm/Xfdesktop trong Xvfb trên Ubuntu WSL, cùng test cài lại/khôi phục Xfconf/Plank và test rollback LightDM. **Chưa kiểm thử đăng nhập LightDM hoặc toàn bộ desktop Kali trên máy thật/VM.**

Trên máy test, clone nhánh hỗ trợ Kali:

```bash
git clone --branch kali-linux https://github.com/phamquangvinhfpt/mactahoe-ubuntu.git
cd mactahoe-ubuntu
./install.sh
```

Nếu đã clone repo này:

```bash
git fetch origin
git switch kali-linux
git pull --ff-only origin kali-linux
./install.sh
```

Đăng xuất rồi đăng nhập lại sau khi cài. Gỡ bằng `./uninstall.sh`; chạy trong Xfce nếu đã cài Xfce để khôi phục các thuộc tính Xfconf đã sao lưu. Cài lại giữ bản sao cấu hình ban đầu. Các tài nguyên theme/icon dùng chung giữa hai desktop.

Nếu muốn thêm GNOME vào Kali Xfce: `sudo apt update && sudo apt install kali-desktop-gnome`, sau đó đăng xuất và chọn phiên GNOME. Xem [hướng dẫn Kali chính thức](https://www.kali.org/docs/general-use/switching-desktop-environments/).

## Hình ảnh

<p align="center"><img src="assets/screenshots/mactahoe-desktop.png" alt="Desktop MacTahoe trên GNOME với widget và dock" width="100%"></p>

<table>
  <tr>
    <th align="center">GNOME Overview</th>
    <th align="center">Cài đặt hệ thống & Trình quản lý tệp</th>
  </tr>
  <tr>
    <td><img src="assets/screenshots/mactahoe-overview.png" alt="GNOME Overview với giao diện MacTahoe" width="100%"></td>
    <td><img src="assets/screenshots/mactahoe-settings.png" alt="GNOME Settings và Files theo giao diện MacTahoe" width="100%"></td>
  </tr>
  <tr>
    <th align="center">Quản lý icon MacTahoe</th>
    <th align="center">Giao diện ứng dụng (Firefox & Brave)</th>
  </tr>
  <tr>
    <td><img src="assets/screenshots/mactahoe-icon-manager.png" alt="Ứng dụng thay thế icon MacTahoe cho các ứng dụng" width="100%"></td>
    <td><img src="assets/screenshots/mactahoe-app-themer.png" alt="Ứng dụng chỉnh giao diện Tahoe cho Firefox và Brave" width="100%"></td>
  </tr>
  <tr>
    <th align="center">Quản lý và tuỳ chỉnh tiện ích</th>
    <th align="center">Trình duyệt hiển thị (Safari Tahoe & Brave)</th>
  </tr>
  <tr>
    <td><img src="assets/screenshots/mactahoe-extensions.png" alt="Quản lý và tuỳ chỉnh tiện ích mở rộng" width="100%"></td>
    <td><img src="assets/screenshots/mactahoe-browsers.png" alt="Trình duyệt hiển thị giao diện macOS Tahoe" width="100%"></td>
  </tr>
</table>

## Nội dung đã gom

- `vendor/MacTahoe-gtk-theme/` và `vendor/MacTahoe-icon-theme/`: snapshot nguồn theme, đã bỏ metadata Git lồng bên trong.
- `assets/fonts/SF-Pro/` và `assets/fonts/SF-Mono/`: font đang dùng.
- `assets/wallpapers/`: wallpaper ngày và đêm.
- `assets/screenshots/`: ảnh giới thiệu desktop, Overview và giao diện ứng dụng.
- `apps/`: trình quản lý icon MacTahoe, cùng mã nguồn và test cho **Âm lịch Việt Nam** (`apps/am-lich-viet-nam/`), **Nén ảnh** (`apps/image-compressor/`) và **Giao diện ứng dụng** (`apps/mactahoe-app-themer/`).
- `desktop/`: launcher ứng dụng.
- `vendor/gnome-extensions/`: các tiện ích độc quyền gồm giao diện hợp nhất **UbuntuTahoe**, thanh dock macOS **UbuntuTahoeDock** (có sẵn icon Launchpad) và bộ widget desktop Native **UbuntuTahoeWidgets** (thay thế hoàn toàn Conky, tích hợp OpenWeather).
- `docs/extension-settings/current-gnome-extensions.md`: các extension đang bật và cấu hình Blur/My Shell, Global Menu trên máy.
- `docs/skin-tahoe-source.md`: hướng dẫn cấu hình ban đầu.
- `config/gsettings.tsv`: tùy chọn GNOME, dock và extension được áp dụng.
- `config/firefox-user.js`: tùy chọn cần cho CSS theme Firefox.

## Thành phần giao diện

- Theme GTK/GNOME Shell, bộ icon MacTahoe, con trỏ, font SF và wallpaper tạo phần giao diện nền.
- Topbar dùng kiểu trong suốt vĩnh viễn (`#panel` trong CSS); không cần bật blur để có nền trong suốt.
- Firefox bo góc 24 px khi cửa sổ ở trạng thái thường (chuẩn macOS Tahoe) và bỏ bo góc khi phóng tối đa; loại bỏ viền đen ngoài khung CSD.
- **UbuntuTahoe** là tiện ích giao diện hợp nhất độc quyền cho bộ theme, tích hợp sẵn Global Menu, chuyển đồng hồ sang góc phải, hiệu ứng mờ kính Overview & thư mục ứng dụng và bộ gõ. Người dùng chỉ cần một công tắc bật duy nhất mà không cần cài đặt nhiều extension riêng rẽ.
- **UbuntuTahoeDock** là tiện ích Dock độc quyền chuẩn phong cách macOS Tahoe (nổi ở đáy màn hình, bo cong kính mờ, đèn báo 1 chấm tròn DOT, tự ẩn thông minh, có thanh trượt chỉnh kích thước icon). Nhờ có UbuntuTahoeDock, bộ giao diện hoàn toàn độc lập và không phụ thuộc vào Ubuntu Dock của hệ thống, tương thích mượt mà trên mọi bản phân phối Linux dùng GNOME.
- GNOME Tweaks và Extension Manager là ứng dụng quản lý tùy chọn/extension, không phải thành phần tạo giao diện. Trình quản lý icon MacTahoe, launcher widget, **Âm lịch Việt Nam** và **Nén ảnh** được đóng gói trong repo.
- Bộ cài cài hai ứng dụng vào menu GNOME, kèm icon và launcher; Âm lịch chạy offline, còn Nén ảnh xử lý tệp cục bộ bằng Pillow.
- Extension được kiểm tra theo phiên bản GNOME Shell khai báo trong metadata và chỉ được bật cho lần đăng nhập tiếp theo. Bộ tiện ích độc quyền (**UbuntuTahoe**, **UbuntuTahoeDock**, **UbuntuTahoeWidgets**) tương thích toàn diện từ **GNOME Shell 45 đến 51+** (đã chuẩn hóa sang `Meta.CursorTracker` và `Clutter.Orientation`, loại bỏ hoàn toàn các API cũ như `pointerWatcher.js` và thuộc tính `vertical`).

## Cài đặt & Cập nhật

### Cài đặt lần đầu (Tải & Cài tự động)

Mở Terminal ở bất kỳ thư mục nào, dán nguyên lệnh này để tải repo rồi tự động cài đặt:

```bash
cd "$HOME" && if [ -d mactahoe-ubuntu/.git ]; then git -C mactahoe-ubuntu pull --ff-only; else git clone https://github.com/adfoxtheme/mactahoe-ubuntu.git mactahoe-ubuntu; fi && cd "$HOME/mactahoe-ubuntu" && ./install.sh
```

### Cập nhật mã nguồn mới & Cài đặt lại (Update & Reinstall)

Khi repo có bản cập nhật mới (như thêm tính năng cho thanh Dock, tiện ích Widgets, ứng dụng mới hoặc sửa lỗi), dán lệnh sau vào Terminal để tự động kéo code mới nhất từ GitHub và cài đặt lại ngay lập tức:

```bash
cd "$HOME/mactahoe-ubuntu" && git pull && ./install.sh
```

Sau khi cài xong, đăng xuất (Log out) rồi đăng nhập lại để GNOME nạp phiên bản mới của các tiện ích mở rộng.

### Đồng bộ màn hình đăng nhập (GDM)

Nếu muốn màn hình đăng nhập (login) cũng đồng bộ giao diện Ubuntu Tahoe thì chạy tiếp lệnh dưới:

```bash
cd "$HOME/mactahoe-ubuntu" && ./install-gdm.sh
```

> [!CAUTION]
> **CÀI GDM CÓ THỂ LÀM HỎNG MÀN HÌNH ĐĂNG NHẬP.** Đây là màn hình đăng nhập của hệ thống (GDM), không phải màn hình khóa trong phiên GNOME. Bước này thay resource GDM của hệ thống (Yaru trên Ubuntu hoặc Adwaita trên Debian) bằng resource theme đã biên dịch. Nếu resource không tương thích hoặc có lỗi ngoài bước kiểm tra, GDM có thể hiện màn hình đen hoặc không cho đăng nhập; điều này có thể trông giống GNOME bị treo.
>
> Chỉ chạy nếu bạn chấp nhận rủi ro và biết cách vào TTY/khôi phục máy; nên tạo snapshot máy ảo hoặc bản sao lưu trước. Không chạy bằng `sudo ./install-gdm.sh` — script sẽ tự yêu cầu quyền quản trị khi cần.
>
> Nếu GDM lỗi, chuyển sang TTY (`Ctrl`+`Alt`+`F3`; trong VirtualBox dùng **Host key** + `F3`, thường là `Right Ctrl` + `F3`), đăng nhập tài khoản thường rồi khôi phục resource GDM:
>
> ```bash
> sudo "$HOME/mactahoe-ubuntu/vendor/MacTahoe-gtk-theme/tweaks.sh" -g -r
> sudo reboot
> ```
>
> Lệnh khôi phục trên giả định repo nằm ở `~/mactahoe-ubuntu`; nếu lưu ở chỗ khác, thay bằng đường dẫn repo thực tế. Nếu lần chạy dừng ở bước kiểm tra/biên dịch trước khi áp dụng, GDM chưa bị thay đổi.

Bộ widget desktop được tích hợp trực tiếp qua tiện ích mở rộng **UbuntuTahoeWidgets**, hoàn toàn không cần cài đặt Conky hay chạy tiến trình nền bên ngoài. Người dùng có thể tùy chỉnh bật/tắt từng widget (Đồng hồ lớn, Thời tiết OpenWeather, Hệ thống, Âm lịch, Nhắc nghỉ), nhập API Key và căn lề ngay trong ứng dụng **Tiện ích mở rộng (Extension Manager)**.

### Sau khi cài

1. Chờ Terminal báo `Installed`, sau đó đăng xuất rồi đăng nhập lại để GNOME nạp theme và các extension. Sau khi cài riêng GDM bằng `install-gdm.sh`, khởi động lại máy.
2. Mở **Tiện ích mở rộng (Extension Manager)**, bật tiện ích **UbuntuTahoeWidgets** để hiển thị bộ widget desktop và vào phần Cài đặt để tùy chỉnh theo ý muốn.
3. Mở **Quản lý icon MacTahoe** trong danh sách ứng dụng để chọn icon riêng cho ứng dụng. Font, con trỏ, bộ icon/theme tổng thể và tiện ích **UbuntuTahoe**, **UbuntuTahoeDock** đã được tự động cài đặt và kích hoạt sẵn trọn bộ giao diện macOS Tahoe.
4. **Âm lịch Việt Nam**, **Nén ảnh** và **Giao diện ứng dụng** được cài thành các ứng dụng riêng, có thể mở từ danh sách ứng dụng GNOME hoặc chạy `am-lich-viet-nam`, `image-compressor`, `mactahoe-app-themer` trong Terminal.
5. Nếu không thấy thay đổi, kiểm tra Terminal đã hiện thông báo `Installed` chưa; nếu có, thử đăng xuất/đăng nhập lại một lần nữa.

### Quản lý và tuỳ chỉnh tiện ích mở rộng

Người dùng có thể quản lý và tùy chỉnh các tiện ích mở rộng độc quyền của bộ giao diện ngay trong ứng dụng **Trình quản lý tiện ích (Extension Manager)** hoặc **Tiện ích (Extensions)**:

#### 1. Thanh Dock macOS (UbuntuTahoeDock)
Bấm vào nút **Bánh răng (Cài đặt)** cạnh `UbuntuTahoeDock` (hoặc chạy lệnh: `gnome-extensions prefs UbuntuTahoeDock@adfoxtheme.github.io`):
- **Hành vi thanh Dock:**
  - *Ẩn khi ứng dụng full:* Tự động ẩn thông minh khi cửa sổ phóng to tối đa hoặc toàn màn hình.
  - *Luôn ẩn:* Luôn ẩn dưới mép màn hình, chỉ xuất hiện khi rê chuột tới.
  - *Luôn hiển thị:* Dock nổi cố định trên ứng dụng chuẩn macOS, không làm co cửa sổ và không chừa khoảng trống bên dưới.
- **Kích thước Dock:** Thanh trượt điều chỉnh kích thước biểu tượng Dock (mặc định chuẩn 45px).

#### 2. Widget Desktop (UbuntuTahoeWidgets)
Bấm vào nút **Bánh răng (Cài đặt)** cạnh `UbuntuTahoeWidgets` (hoặc chạy lệnh: `gnome-extensions prefs UbuntuTahoeWidgets@adfoxtheme.github.io`):
- **Bật / Tắt từng widget:** Có công tắc độc lập cho từng widget:
  - *Đồng hồ lớn (Clock):* Đồng hồ số viền kính phong cách macOS Tahoe đặt bên trái.
  - *Thời tiết (Weather):* Thông tin thời tiết chi tiết, nhiệt độ, độ ẩm và gió.
  - *Giám sát hệ thống (System Metrics):* Trực quan hóa tải CPU (tự động nhận diện tên chip), GPU (tự động nhận diện card rời NVIDIA & AMD Radeon RX, tự động ẩn gọn gàng khi chỉ dùng card onboard iGPU), RAM, ổ cứng SSD và tốc độ mạng.
  - *Âm lịch Việt Nam (Lunar Calendar):* Lịch âm truyền thống Việt Nam.
  - *Nhắc nhở nghỉ ngơi (Rest Reminder):* Theo dõi thời gian làm việc và nhắc nhở nghỉ ngơi.
  *(Khi tắt một widget bên phải, các widget còn lại sẽ tự động dồn lên, không để lại khoảng trống trên màn hình).*
- **Cấu hình thời tiết OpenWeather:**
  - Nhập **API Key OpenWeather** cá nhân (nếu để trống, tiện ích sẽ tự động dùng nguồn dữ liệu Open-Meteo miễn phí).
  - Đặt **Tên thành phố** (ví dụ: `Hà Nội`, `Hồ Chí Minh`, `Đà Nẵng`...).
  - Điều chỉnh chu kỳ làm mới dữ liệu (mặc định 15 phút).
- **Căn chỉnh vị trí & lề màn hình:**
  - Tùy chỉnh khoảng cách lề trái và lề trên của Đồng hồ lớn.
  - Tùy chỉnh khoảng cách lề phải và lề trên của Cụm widget để vừa vặn hoàn hảo với mọi độ phân giải màn hình.

### Hỗ trợ & Kiểm thử trên Ubuntu 26.04, Debian 13, Fedora & CachyOS (Arch)

Repo được hỗ trợ đầy đủ và kiểm thử thực tế (tested) thành công trên:
- **Ubuntu 26.04 LTS** (APT, Snap Firefox, Yaru GDM)
- **Debian 13 (Trixie)** (APT, Mozilla APT / ESR Firefox, Adwaita GDM)
- **Fedora 40, 41, 42+** (DNF, RPM / Flatpak Firefox, Adwaita GDM + SELinux)
- **CachyOS GNOME / Arch Linux** (Pacman, Native / Flatpak Firefox, Adwaita GDM)
với môi trường GNOME 48 trở lên.

Bộ cài tự động phát hiện trình quản lý gói phù hợp (`pacman` trên CachyOS/Arch, `dnf` trên Fedora, `apt-get` trên Ubuntu/Debian) và cài đặt đúng các gói tương thích.

Trên Debian, để có trải nghiệm giao diện Firefox chuẩn Safari/macOS Tahoe đẹp nhất, khuyến nghị cài đặt Firefox bản mới nhất từ kho chính thức của Mozilla (Mozilla APT) thay vì dùng bản Firefox ESR cũ:

```bash
sudo apt install -y wget
sudo mkdir -p /etc/apt/keyrings
sudo wget -qO /etc/apt/keyrings/packages.mozilla.org.asc \
    https://packages.mozilla.org/apt/repo-signing-key.gpg
echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" \
    | sudo tee /etc/apt/sources.list.d/mozilla.list
echo -e 'Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000' | \
    sudo tee /etc/apt/preferences.d/mozilla
sudo apt update && sudo apt install -y firefox
```

Bộ cài `install.sh` tự động nhận diện và đồng bộ theme Firefox trên cả 4 cấu hình đường dẫn:
1. `${XDG_CONFIG_HOME:-$HOME/.config}/mozilla/firefox` *(Debian / Mozilla APT / Fedora hiện đại)*
2. `$HOME/.mozilla/firefox` *(Debian ESR, Fedora RPM native, ...)*
3. `$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox` *(Fedora / Linux Flatpak)*
4. `$HOME/snap/firefox/common/.mozilla/firefox` *(Ubuntu Snap)*

Nếu Firefox vừa cài đặt mà chưa từng mở lần nào, `install.sh` cũng sẽ tự động chạy tiến trình ngầm để khởi tạo profile chuẩn trước khi nạp giao diện Tahoe.

### Gỡ cài đặt

Để gỡ giao diện, tiện ích và khôi phục các file đã sao lưu (giữ lại thư mục repo để có thể cài lại), mở Terminal ở bất kỳ vị trí nào và chạy:

```bash
cd "$HOME/mactahoe-ubuntu" && ./uninstall.sh
```

Chạy bằng tài khoản thường, không thêm `sudo`; trình gỡ sẽ hỏi xác nhận trước khi khôi phục bản sao cấu hình GNOME. Nếu đã cài theme màn hình đăng nhập, lệnh này cũng sẽ yêu cầu mật khẩu sudo để khôi phục. Các gói hệ thống được giữ lại.

Bộ cài (cả `install.sh` và `install-gdm.sh`) đã được kiểm thử và hỗ trợ đầy đủ trên **Ubuntu 26.04**, **Debian 13**, **Fedora** và **CachyOS / Arch Linux** (GNOME 48 trở lên). Bộ cài GDM kiểm tra dịch vụ GDM đang có (`gdm` trên CachyOS/Arch/Fedora, `gdm3` trên Ubuntu/Debian), tự động nhận diện gói và resource phù hợp cho từng hệ thống (Yaru trên Ubuntu hoặc Adwaita trên Debian/Fedora/CachyOS) trước khi áp dụng giao diện Tahoe. Trên Fedora, script tự động phục hồi context bảo mật SELinux (`restorecon`) sau khi cập nhật resource GDM để đăng nhập luôn an toàn và ổn định. Bước này thay đổi resource màn hình đăng nhập hệ thống; chạy riêng và reboot sau khi cài.

## Nguồn và phiên bản theme

- MacTahoe GTK: commit `1e45e19` theo tài liệu cấu hình.
- MacTahoe icons: commit `839848b9` theo tài liệu cấu hình.
- Theme gốc có hướng dẫn và thông tin giấy phép bên trong từng thư mục `vendor/`.

Font SF Pro được đưa kèm trong repo. Hãy kiểm tra điều khoản giấy phép trước khi phân phối lại.
