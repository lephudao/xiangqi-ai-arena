/**
 * Giao diện quản lý API key.
 *
 * Mỗi nhà cung cấp một dòng: ô nhập (luôn `type=password`), trạng thái, nút Lưu/Xoá, và
 * đường lấy key miễn phí. Sau khi lưu chỉ hiện dạng che — quay màn hình là hoạt động chính
 * của dự án này nên key không bao giờ được hiện nguyên văn.
 */

import { PROVIDERS, clearAll, clearKey, getKey, maskKey, saveKey } from "./key-vault.js";

/**
 * Lời giải thích key đi đâu. Khác nhau theo chế độ, và phải nói THẬT.
 *
 * Ở chế độ Local, key đánh cờ buộc phải đi tới máy chủ Flask vì vòng lặp trọng tài chạy ở
 * đó. Hứa "key không rời máy bạn" trong trường hợp đó là nói dối — dù máy chủ ấy chạy trên
 * chính máy người dùng.
 */
function noticeFor(mode) {
    if (mode === "local") {
        return `Key lưu trong trình duyệt của bạn (localStorage). Máy chủ đang chạy trên
            <strong>chính máy này</strong>, và key được gửi tới nó để gọi API đánh cờ —
            giữ trong bộ nhớ tạm, không ghi ra đĩa, không ghi vào nhật ký, không trả lại
            trong bất kỳ phản hồi nào. Riêng phần đọc tiếng gọi thẳng từ trình duyệt.`;
    }
    return `Key lưu trong trình duyệt của bạn (localStorage) và gửi <strong>thẳng</strong>
        tới nhà cung cấp AI. Trang này không có máy chủ nào — không ai ngoài bạn và nhà cung
        cấp thấy được key. Bạn tự trả tiền cho key của mình; nên dùng key có giới hạn chi tiêu.`;
}

function buildRow(provider, onChange) {
    const row = document.createElement("div");
    row.className = "key-row";

    const label = document.createElement("span");
    label.className = "key-provider";
    label.textContent = provider.label;

    const input = document.createElement("input");
    input.type = "password";          // không bao giờ hiện nguyên văn, kể cả lúc đang gõ
    input.autocomplete = "off";
    input.className = "key-input";

    const status = document.createElement("span");
    status.className = "key-status";

    const save = document.createElement("button");
    save.type = "button";
    save.className = "btn btn-secondary btn-small";

    const help = document.createElement("a");
    help.href = provider.signup;
    help.target = "_blank";
    help.rel = "noopener";
    help.className = "key-help";
    help.textContent = "lấy key";

    const render = () => {
        const stored = getKey(provider.id);
        if (stored) {
            input.value = "";
            input.placeholder = maskKey(stored);
            status.textContent = "✅ đã lưu";
            status.classList.remove("missing");
            save.textContent = "Xoá";
        } else {
            input.placeholder = "dán key vào đây…";
            status.textContent = "⚠️ chưa có";
            status.classList.add("missing");
            save.textContent = "Lưu";
        }
    };

    save.addEventListener("click", () => {
        if (getKey(provider.id)) {
            clearKey(provider.id);
        } else {
            saveKey(provider.id, input.value);
        }
        render();
        onChange();
    });
    // Enter trong ô nhập cũng lưu — người dùng dán key xong hay bấm Enter theo phản xạ
    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !getKey(provider.id)) {
            event.preventDefault();
            save.click();
        }
    });

    render();
    row.append(label, input, status, save, help);
    return row;
}

/**
 * Dựng khu quản lý key. `onChange` được gọi mỗi khi kho key đổi, để giao diện cập nhật lại
 * cảnh báo "model này chưa có key".
 */
export function renderKeyVault({ mode, onChange = () => {} }) {
    document.getElementById("key-notice").innerHTML = noticeFor(mode);

    const container = document.getElementById("key-vault-rows");
    container.innerHTML = "";
    PROVIDERS.forEach(provider => container.appendChild(buildRow(provider, onChange)));

    const clearButton = document.getElementById("btn-clear-keys");
    clearButton.onclick = () => {
        clearAll();
        renderKeyVault({ mode, onChange });
        onChange();
    };
}
